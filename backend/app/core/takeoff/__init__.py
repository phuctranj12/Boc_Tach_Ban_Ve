"""Registry bóc tách khối lượng (QS) từ sơ đồ — dễ scale nhiều loại bản vẽ.

Thêm một kiểu bản vẽ mới = thêm 1 module có 2 hàm:
    detect_score(page) -> float        # điểm khả năng khớp kiểu này
    extract(page, page_index) -> TakeoffResult

và (TUỲ CHỌN) hàm thứ 3 khi loại bản vẽ đó không hợp với thước đo mặc định:
    quality(res) -> int                # số dòng bóc ĐÚNG, thang 0..len(items)

rồi đăng ký vào EXTRACTORS. Phần còn lại (auto-detect, API, frontend, BOQ) không
phải sửa.
"""
from __future__ import annotations

import fitz

from .base import TakeoffResult, result_quality
from . import (busbar_slash, panel_table, hotel_db, mep_floorplan, cdc_elv_unit,
               orient, outlined_text)

# thứ tự không quan trọng — chọn theo điểm cao nhất
EXTRACTORS = {
    "busbar_slash": busbar_slash,
    "panel_table": panel_table,
    "hotel_db": hotel_db,
    "mep_tray": mep_floorplan,
    "cdc_elv_unit": cdc_elv_unit,
}


def quality(res: TakeoffResult) -> int:
    """Điểm CHẤT LƯỢNG dùng để chọn hướng xoay. Mặc định đếm lộ có 'size' (bóc sai
    hướng ⇒ cáp không gắn được ⇒ size rỗng). Loại bản vẽ mà cáp KHÔNG ghi tiết diện
    (vd điện nhẹ: UTP/quang) thì thước đo đó luôn = 0 ở mọi hướng, trọng tài hoá mù
    — nên module tự khai `quality` riêng."""
    mod = EXTRACTORS.get(res.diagram_type)
    fn = getattr(mod, "quality", None) if mod else None
    return fn(res) if fn else result_quality(res)


def detect_type(page: fitz.Page) -> tuple[str, dict]:
    scores = {name: mod.detect_score(page) for name, mod in EXTRACTORS.items()}
    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return "unknown", scores
    return best, scores


def _extract_core(page: fitz.Page, page_index: int, kind: str) -> TakeoffResult:
    """Bóc tách trên trang đã đúng hướng (không tự xoay)."""
    scores = {}
    if kind == "auto":
        kind, scores = detect_type(page)
    if kind == "unknown" or kind not in EXTRACTORS:
        res = TakeoffResult(page=page_index, diagram_type="unknown")
        res.debug = {"scores": scores, "error": "Không nhận diện được loại sơ đồ."}
        # Không nhận ra loại thì tìm hiểu VÌ SAO: nếu chữ đã bị convert thành nét khi
        # xuất PDF thì không extractor nào bóc được, phải báo rõ cho người dùng.
        # Chỉ chạy ở nhánh thất bại nên không làm chậm đường chạy bình thường.
        flag = outlined_text.check(page)
        if flag:
            res.debug.update(flag)
            res.debug["error"] = flag["message"]
        return res
    res = EXTRACTORS[kind].extract(page, page_index)
    res.debug["scores"] = scores
    return res


def extract_takeoff(page: fitz.Page, page_index: int, kind: str = "auto") -> TakeoffResult:
    # Ép loại + không tự xoay: bóc thẳng.
    if kind != "auto":
        res = _extract_core(page, page_index, kind)
        res.debug["rotation"] = 0
        return res

    # Fast path: thử hướng GỐC trước. Nhận NGAY nếu kết quả CHẤT LƯỢNG (đa số lộ có
    # cáp) — đúng hướng thì cáp gắn được. KHÁC bản cũ ("có lộ là nhận"): tránh nhận
    # nhầm kết quả RÁC khi bản vẽ bị xoay (hotel_db ở hướng sai ra nhiều lộ nhưng 0 cáp).
    res0 = _extract_core(page, page_index, "auto")
    q0 = quality(res0)
    if res0.items and q0 >= 0.6 * len(res0.items):
        res0.debug["rotation"] = 0
        return res0

    # Hướng gốc kém/không ra -> nội dung có thể bị xoay. Thử cả 90/180/270 rồi chọn
    # hướng theo (CHẤT LƯỢNG, số lộ) — quality phân biệt được cả hướng ra-rác.
    best = (res0, 0, (q0, len(res0.items)))
    for rot in (90, 180, 270):
        holder, rp = orient.rotate_page(page, rot)
        try:
            res = _extract_core(rp, page_index, "auto")
        finally:
            if holder is not None:
                holder.close()
        key = (quality(res), len(res.items))
        if key > best[2]:
            best = (res, rot, key)

    res, rot, _ = best
    res.debug["rotation"] = rot
    return res


def extract_takeoff_from_pdf(path: str, page_index: int, kind: str = "auto") -> TakeoffResult:
    doc = fitz.open(path)
    try:
        return extract_takeoff(doc[page_index], page_index, kind)
    finally:
        doc.close()
