"""Các tool MCP — vỏ mỏng gọi thẳng logic nội bộ (không tự HTTP vào chính mình).

Quy tắc (theo khung tích hợp MCP):
  * Docstring của tool là API cho model đọc — liệt kê enum ngay trong docstring.
  * Lỗi nghiệp vụ -> raise ToolError("thông điệp tiếng Việt rõ"), không return {"error": ...}.
  * Kiểu trả về cụ thể (dict[str, Any]) để MCP sinh outputSchema.
"""
from __future__ import annotations

import uuid
from typing import Any
from urllib.request import Request as _UrlRequest, urlopen

import fitz
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from ..config import UPLOAD_DIR
from ..core import export
from ..core.pipeline import run_pipeline
from ..core.qa import answer as _qa_answer
from ..core.takeoff import extract_takeoff, extract_takeoff_from_pdf
from ..core.takeoff.sheet_meta import extract_meta
from ..sheet_config import runner as _sc_runner
from ..sheet_config.version import __version__ as _sc_version
from ..storage import review_store, store

# Bản vẽ vector hiếm khi > vài MB; chặn tải file quá lớn qua URL.
_MAX_PDF_BYTES = 40 * 1024 * 1024
_KINDS = ("auto", "panel_table", "busbar_slash", "hotel_db", "mep_tray")


def _pdf_path(job_id: str):
    p = UPLOAD_DIR / f"{job_id}.pdf"
    if not p.exists():
        raise ToolError(
            f"Không tìm thấy PDF cho job_id={job_id!r}. "
            "Job có thể đã mất do Space restart — gọi lại analyze_pdf."
        )
    return p


def _ingest(content: bytes, filename: str) -> dict[str, Any]:
    if content[:5] != b"%PDF-":
        raise ToolError("Dữ liệu không phải file PDF (thiếu chữ ký %PDF-).")
    job_id = uuid.uuid4().hex[:12]
    dest = UPLOAD_DIR / f"{job_id}.pdf"
    dest.write_bytes(content)
    try:
        result = run_pipeline(str(dest), job_id, filename)
    except Exception as exc:  # noqa: BLE001 — trả lỗi gọn cho model
        dest.unlink(missing_ok=True)
        raise ToolError(f"Phân tích PDF thất bại: {exc}") from exc
    store.save_result(result)
    data = result.model_dump()
    return {
        "job_id": job_id,
        "filename": filename,
        "page_count": data["page_count"],
        "sheets": data["sheets"],
        "stats": data.get("stats", {}),
    }


def _confirm_all(job_id: str) -> dict[str, Any]:
    doc = fitz.open(str(_pdf_path(job_id)))
    confirmed = 0
    try:
        for page in range(doc.page_count):
            saved = review_store.get_page(job_id, page)
            if saved:
                payload = {
                    "diagramType": saved.get("diagramType", ""),
                    "panelName": saved.get("panelName", ""),
                    "panels": saved.get("panels", []),
                    "meta": saved.get("meta"),
                    "items": saved.get("items", []),
                    "confirmed": True,
                }
            else:
                res = extract_takeoff(doc[page], page).to_dict()
                if not res["items"]:
                    continue
                payload = {
                    "diagramType": res["diagramType"],
                    "panelName": res["panelName"],
                    "panels": res.get("panels", []),
                    "meta": extract_meta(doc[page]),
                    "items": res["items"],
                    "confirmed": True,
                }
            review_store.save_page(job_id, page, payload)
            confirmed += 1
    finally:
        doc.close()
    return {"confirmed_pages": confirmed}


async def _sheet_config(target: str, source: str) -> dict[str, Any]:
    try:
        status, body = await _sc_runner.call(
            "POST", target, body=source.encode("utf-8"),
            headers={"content-type": "text/plain"}, version=_sc_version,
        )
    except _sc_runner.SheetConfigUnavailable as exc:
        raise ToolError(f"Module Sheet Configure không sẵn sàng: {exc}") from exc
    import json as _json

    parsed = _json.loads(body)
    parsed["_http_status"] = status
    return parsed


def register_tools(mcp: FastMCP) -> None:
    # ---------------- Bóc tách bản vẽ ----------------

    @mcp.tool()
    def analyze_pdf(pdf_url: str | None = None, pdf_base64: str | None = None,
                    filename: str = "ban_ve.pdf") -> dict[str, Any]:
        """Nạp một PDF bản vẽ MEP và phân tích. Truyền ĐÚNG MỘT trong hai:

        - `pdf_url`: URL công khai tải trực tiếp file .pdf (server tự tải về).
        - `pdf_base64`: nội dung file .pdf đã mã hoá base64 (chỉ nên dùng cho file nhỏ).

        Chỉ nhận PDF vector xuất từ CAD; PDF scan ảnh sẽ không bóc được.
        Trả về `job_id` (dùng cho mọi tool sau), `page_count`, và `sheets[]` gồm
        loại từng trang (`sheet_type`: single_line, panel_schedule, legend,
        lighting_layout, power_layout, plumbing, ...).
        """
        if bool(pdf_url) == bool(pdf_base64):
            raise ToolError("Truyền đúng một trong `pdf_url` hoặc `pdf_base64`.")
        if pdf_url:
            try:
                req = _UrlRequest(pdf_url, headers={"User-Agent": "boc-tach-mcp"})
                with urlopen(req, timeout=120) as resp:  # noqa: S310 — URL do người dùng cấp
                    content = resp.read(_MAX_PDF_BYTES + 1)
            except Exception as exc:  # noqa: BLE001
                raise ToolError(f"Không tải được PDF từ URL: {exc}") from exc
        else:
            import base64
            try:
                content = base64.b64decode(pdf_base64, validate=True)
            except Exception as exc:  # noqa: BLE001
                raise ToolError(f"pdf_base64 không hợp lệ: {exc}") from exc
        if len(content) > _MAX_PDF_BYTES:
            raise ToolError(f"File vượt {_MAX_PDF_BYTES // (1024 * 1024)} MB.")
        return _ingest(content, filename)

    @mcp.tool()
    def list_jobs() -> dict[str, Any]:
        """Liệt kê các job phân tích còn lưu trên server (mất khi Space restart)."""
        return {"jobs": store.list_results()}

    @mcp.tool()
    def extract_page(job_id: str, page: int = 0, kind: str = "auto") -> dict[str, Any]:
        """Bóc tách khối lượng cáp & ống luồn của MỘT trang. `page` bắt đầu từ 0.

        `kind`: "auto" (mặc định, tự nhận diện) hoặc ép loại sơ đồ:
        "panel_table" | "busbar_slash" | "hotel_db" | "mep_tray".
        Trả về `diagramType`, `panels[]`, và `items[]` — mỗi item gồm panelName,
        roadName, loadName, itemGroup, itemName, size, cableSpec, conduit.
        """
        if kind not in _KINDS:
            raise ToolError(f"kind={kind!r} không hợp lệ. Chọn: {', '.join(_KINDS)}.")
        path = _pdf_path(job_id)
        doc = fitz.open(str(path))
        n = doc.page_count
        doc.close()
        if page < 0 or page >= n:
            raise ToolError(f"Trang {page} ngoài khoảng [0, {n - 1}].")
        return extract_takeoff_from_pdf(str(path), page, kind).to_dict()

    @mcp.tool()
    def get_boq(job_id: str, confirm_all: bool = True) -> dict[str, Any]:
        """Xuất BOQ (bảng khối lượng) gộp toàn bộ dự án dạng mảng phẳng.

        `confirm_all=True` (mặc định): tự bóc + chốt mọi trang trước khi xuất.
        `confirm_all=False`: chỉ lấy các trang đã được chốt/lưu từ trước.
        Trả về `rows[]` — mỗi dòng là một tuyến cáp/ống với đủ trường như `extract_page`.
        """
        summary = _confirm_all(job_id) if confirm_all else {}
        rows = export.to_json(job_id, only_confirmed=True)
        return {"job_id": job_id, "count": len(rows), "rows": rows, **summary}

    @mcp.tool()
    def ask_drawing(job_id: str, question: str) -> dict[str, Any]:
        """Hỏi–đáp rule-based về quan hệ trong bản vẽ đã phân tích (điều khiển,
        cấp nguồn, tổng công suất đèn theo khu vực...). Trả về `answer` + `items`.
        """
        res = store.get_result(job_id)
        if not res:
            raise ToolError(f"Không tìm thấy kết quả cho job_id={job_id!r}.")
        if not question.strip():
            raise ToolError("`question` rỗng.")
        return _qa_answer(res, question)

    # ---------------- Sheet Configure (luồng độc lập) ----------------

    @mcp.tool()
    async def normalize_sheet_config(source: str, strict: bool = True) -> dict[str, Any]:
        """Chuẩn hoá cấu hình bộ bản vẽ shop (`DocumentSetConfig`): nhận JSON/JSONC
        viết tay (cho phép `//`, `/* */`, dấu phẩy thừa) -> JSON hợp lệ.

        `strict=True` (khuyến nghị cho hệ thống tự động): mọi cảnh báo bị coi là
        lỗi (`_http_status` = 422). Kết quả gồm `ok`, `config`, `json` (chuỗi ghi
        thẳng ra file — KHÔNG serialize lại từ `config`), `issues`, `warnings`, `stats`.
        """
        target = "/api/normalize?strict=1" if strict else "/api/normalize"
        return await _sheet_config(target, source)

    @mcp.tool()
    async def validate_sheet_config(config_json: str) -> dict[str, Any]:
        """Kiểm tra 7 luật trên một cấu hình JSON đã có (không phải JSONC).
        Trả về `ok`, `issues[]`, `stats`. `_http_status` = 200 khi hợp lệ, 422 khi không.
        """
        return await _sheet_config("/api/validate", config_json)

    @mcp.tool()
    async def get_sheet_config_template() -> dict[str, Any]:
        """Trả về cấu hình `DocumentSetConfig` mặc định (3 bộ, 25 sheet) để dựng form."""
        try:
            status, body = await _sc_runner.call(
                "GET", "/api/template", version=_sc_version,
            )
        except _sc_runner.SheetConfigUnavailable as exc:
            raise ToolError(f"Module Sheet Configure không sẵn sàng: {exc}") from exc
        import json as _json

        return {"_http_status": status, "template": _json.loads(body)}
