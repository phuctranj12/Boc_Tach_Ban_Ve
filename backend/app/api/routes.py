"""FastAPI routes: upload/analyze, lấy kết quả, QA, render preview trang."""
from __future__ import annotations

import uuid

import fitz
from fastapi import APIRouter, BackgroundTasks, Body, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from ..config import UPLOAD_DIR
from ..core import export
from ..core.pipeline import run_pipeline
from ..core.qa import answer
from ..core.takeoff import extract_takeoff
from ..core.takeoff.sheet_meta import extract_meta
from ..storage import review_store, store, takeoff_cache

router = APIRouter(prefix="/api")

# Cache kết quả bóc tách theo (job_id, page). Bóc tách 1 trang mất ~2-4s nên nếu
# bóc lại mỗi lần đổi trang sẽ rất chậm. PDF của 1 job không đổi -> cache an toàn,
# không cần huỷ. Trang đã LƯU thì đọc thẳng review_store (ưu tiên trước cache).
#
# 2 tầng: RAM (_EXTRACT_CACHE, nhanh) + đĩa (takeoff_cache) để RESTART không mất.
_EXTRACT_CACHE: dict[tuple[str, int], dict] = {}


def _cache_get(job_id: str, page: int) -> dict | None:
    key = (job_id, page)
    if key in _EXTRACT_CACHE:            # L1: RAM
        return _EXTRACT_CACHE[key]
    disk = takeoff_cache.get_page(job_id, page)  # L2: đĩa (sống qua restart)
    if disk is not None:
        _EXTRACT_CACHE[key] = disk
    return disk


def _cache_put(job_id: str, page: int, payload: dict) -> None:
    _EXTRACT_CACHE[(job_id, page)] = payload
    takeoff_cache.save_page(job_id, page, payload)


def _payload_from_page(doc, page: int) -> dict:
    res = extract_takeoff(doc[page], page).to_dict()
    debug = res.get("debug") or {}
    return {
        "page": page,
        "diagramType": res["diagramType"],
        "panelName": res["panelName"],
        "panels": res["panels"],
        # Lý do bóc không ra (vd chữ đã bị convert thành nét khi xuất PDF) — hiện lên
        # giao diện để người dùng biết phải xử lý gì, thay vì thấy bảng trống.
        "notice": debug.get("message", ""),
        # Thông tin hành chính của trang (dự án/tháp-hầm/khu vực/tầng/điển hình).
        # Đọc được thì điền sẵn, không đọc được để rỗng cho người dùng tự nhập.
        "meta": extract_meta(doc[page]),
        "items": res["items"],
        "confirmed": False,
        "source": "extracted",
    }


def _extract_review(job_id: str, page: int) -> dict:
    cached = _cache_get(job_id, page)
    if cached is not None:
        return cached
    pdf = UPLOAD_DIR / f"{job_id}.pdf"
    if not pdf.exists():
        raise HTTPException(404, "Không tìm thấy file PDF")
    doc = fitz.open(str(pdf))
    try:
        if page < 0 or page >= doc.page_count:
            raise HTTPException(404, "Trang không hợp lệ")
        payload = _payload_from_page(doc, page)
    finally:
        doc.close()
    _cache_put(job_id, page, payload)
    return payload


def _prewarm_extract(job_id: str) -> None:
    """Bóc tách TRƯỚC tất cả trang ngay sau khi upload (chạy nền), lưu cả RAM lẫn
    đĩa để khi duyệt là có sẵn và RESTART không phải bóc lại. Mở PDF 1 lần."""
    pdf = UPLOAD_DIR / f"{job_id}.pdf"
    if not pdf.exists():
        return
    doc = fitz.open(str(pdf))
    try:
        for page in range(doc.page_count):
            if _cache_get(job_id, page) is not None:
                continue
            try:
                _cache_put(job_id, page, _payload_from_page(doc, page))
            except Exception:
                pass  # 1 trang lỗi không chặn các trang còn lại
    finally:
        doc.close()


@router.post("/analyze")
async def analyze(background: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Chỉ chấp nhận file PDF")

    job_id = uuid.uuid4().hex[:12]
    dest = UPLOAD_DIR / f"{job_id}.pdf"
    content = await file.read()
    dest.write_bytes(content)

    try:
        result = run_pipeline(str(dest), job_id, file.filename)
    except Exception as e:  # trả lỗi rõ ràng cho frontend
        raise HTTPException(500, f"Lỗi phân tích: {e}")

    store.save_result(result)
    # Bóc tách sẵn TẤT CẢ trang ở chế độ nền ngay sau khi trả kết quả, để khi
    # người dùng vào duyệt thì đã có sẵn trong cache (không phải chờ từng trang).
    background.add_task(_prewarm_extract, job_id)
    return result.model_dump()


@router.get("/results")
async def results():
    return store.list_results()


@router.get("/results/{job_id}")
async def get_result(job_id: str):
    res = store.get_result(job_id)
    if not res:
        raise HTTPException(404, "Không tìm thấy kết quả")
    return res.model_dump()


@router.get("/results/{job_id}/qa")
async def qa(job_id: str, q: str = Query(..., min_length=1)):
    res = store.get_result(job_id)
    if not res:
        raise HTTPException(404, "Không tìm thấy kết quả")
    return answer(res, q)


@router.get("/results/{job_id}/sld")
async def sld(job_id: str, page: int = Query(0, ge=0), kind: str = Query("auto")):
    """Bóc tách cáp & ống luồn từ Sơ đồ nguyên lý của 1 trang.

    Tự nhận diện loại sơ đồ (busbar+vạch chéo / bảng ma trận / ...) rồi xuất JSON
    theo schema bóc tách khối lượng (QS). Ép kiểu qua tham số `kind`.
    """
    pdf = UPLOAD_DIR / f"{job_id}.pdf"
    if not pdf.exists():
        raise HTTPException(404, "Không tìm thấy file PDF")
    doc = fitz.open(str(pdf))
    try:
        if page < 0 or page >= doc.page_count:
            raise HTTPException(404, "Trang không hợp lệ")
        res = extract_takeoff(doc[page], page, kind)
    finally:
        doc.close()
    return res.to_dict()


# ---------- Human-in-the-loop: duyệt & sửa theo trang ----------
@router.get("/results/{job_id}/review/{page}")
async def get_review(job_id: str, page: int):
    """Lấy dữ liệu trang để duyệt: bản đã lưu nếu có, ngược lại bóc tự động."""
    saved = review_store.get_page(job_id, page)
    if saved:
        return {**saved, "source": "saved"}
    # Bóc tách nặng CPU -> chạy ở threadpool để không khoá event loop (server vẫn
    # phục vụ ảnh preview/điều hướng trong lúc bóc).
    return await run_in_threadpool(_extract_review, job_id, page)


@router.put("/results/{job_id}/review/{page}")
async def put_review(job_id: str, page: int, payload: dict = Body(...)):
    """Lưu dữ liệu đã sửa + cờ xác nhận cho 1 trang."""
    return review_store.save_page(job_id, page, payload)


@router.get("/results/{job_id}/review")
async def review_status(job_id: str):
    return review_store.status(job_id)


# ---------- Xuất BOQ ----------
@router.post("/results/{job_id}/review/confirm-all")
async def confirm_all(job_id: str):
    """Xác nhận TẤT CẢ trang có dữ liệu bóc tách (giữ nguyên chỉnh sửa đã lưu)."""
    pdf = UPLOAD_DIR / f"{job_id}.pdf"
    if not pdf.exists():
        raise HTTPException(404, "Không tìm thấy file PDF")
    doc = fitz.open(str(pdf))
    confirmed = 0
    try:
        for page in range(doc.page_count):
            saved = review_store.get_page(job_id, page)
            if saved:
                items = saved.get("items", [])
                payload = {"diagramType": saved.get("diagramType", ""),
                           "panelName": saved.get("panelName", ""),
                           "panels": saved.get("panels", []),
                           "meta": saved.get("meta"),  # giữ nguyên bản người dùng đã sửa
                           "items": items, "confirmed": True}
            else:
                res = extract_takeoff(doc[page], page).to_dict()
                items = res["items"]
                if not items:
                    continue  # trang không có sơ đồ bóc tách được -> bỏ qua
                payload = {"diagramType": res["diagramType"],
                           "panelName": res["panelName"],
                           "panels": res.get("panels", []),
                           "meta": extract_meta(doc[page]),
                           "items": items, "confirmed": True}
            review_store.save_page(job_id, page, payload)
            confirmed += 1
    finally:
        doc.close()
    return {"confirmed_pages": confirmed, "status": review_store.status(job_id)}


@router.get("/results/{job_id}/export.json")
async def export_json(job_id: str, confirmed: bool = Query(False)):
    text = export.to_json_text(job_id, only_confirmed=confirmed)
    return Response(
        content=text,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="BOQ_{job_id}.json"'},
    )


@router.get("/results/{job_id}/export.xlsx")
async def export_xlsx(job_id: str, confirmed: bool = Query(False)):
    data = export.to_excel(job_id, only_confirmed=confirmed)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="BOQ_{job_id}.xlsx"'},
    )


def _render_preview(job_id: str, page: int, scale: float) -> bytes:
    pdf = UPLOAD_DIR / f"{job_id}.pdf"
    if not pdf.exists():
        raise HTTPException(404, "Không tìm thấy file PDF")
    doc = fitz.open(str(pdf))
    try:
        if page < 0 or page >= doc.page_count:
            raise HTTPException(404, "Trang không hợp lệ")
        pix = doc[page].get_pixmap(matrix=fitz.Matrix(scale, scale))
        return pix.tobytes("png")
    finally:
        doc.close()


@router.get("/results/{job_id}/page/{page}/preview")
async def page_preview(job_id: str, page: int, scale: float = Query(1.0, ge=0.2, le=6.0)):
    png = await run_in_threadpool(_render_preview, job_id, page, scale)
    # Ảnh theo trang không đổi -> cho trình duyệt cache để đổi tới/lui không tải lại.
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})
