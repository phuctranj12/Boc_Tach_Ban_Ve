"""Chuẩn hoá hướng bản vẽ — tiện ích xoay trang.

Bản vẽ CAD luôn axis-aligned nhưng nội dung có thể bị xoay 90/180/270 (text dọc↔
ngang đảo, hoặc lật ngược). `rotate_page` tạo bản xoay (vẫn là vector) để
extract_takeoff thử lại khi hướng gốc không ra kết quả, rồi chọn hướng cho nhiều
lộ nhất (xem __init__.extract_takeoff).

Chỉ xử lý xoay bội số 90° (đặc trưng PDF vector). Bản scan nghiêng góc lẻ cần
pipeline OCR khác — ngoài phạm vi cách vector này.
"""
from __future__ import annotations

import fitz


def rotate_page(page: fitz.Page, rot: int) -> tuple[fitz.Document | None, fitz.Page]:
    """Trang xoay `rot` (vẫn là vector). rot==0 trả thẳng trang gốc.

    Khi rot!=0, doc tạm trả về phải được giữ sống tới khi dùng xong rồi .close().
    """
    if rot == 0:
        return None, page
    src = page.parent
    r = page.rect
    out = fitz.open()
    if rot in (90, 270):
        np = out.new_page(width=r.height, height=r.width)
    else:
        np = out.new_page(width=r.width, height=r.height)
    np.show_pdf_page(np.rect, src, page.number, rotate=rot)
    return out, np
