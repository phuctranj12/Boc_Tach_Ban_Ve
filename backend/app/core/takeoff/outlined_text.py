"""Phát hiện trang bị CONVERT CHỮ THÀNH NÉT khi xuất PDF.

Một số bộ hồ sơ được xuất từ CAD với chữ đã bị "explode" thành đường vector. Khi đó
`page.get_text()` không trả về gì cho phần chữ kỹ thuật (quy cách cáp, dòng điện
aptomat, tên phụ tải…) dù mắt thường vẫn đọc được trên bản in. Không extractor nào
bóc được dữ liệu không tồn tại dưới dạng chữ — nên phải NÓI RÕ cho người dùng thay vì
lặng lẽ trả về 0 dòng và để họ tưởng phần mềm hỏng.

Cách nhận biết — "cụm glyph mồ côi":
  1. Nét có hộp bao cỡ ký tự (rộng 0.5–12pt, cao 1.5–12pt) NHƯNG gấp khúc >=6 đoạn.
     Nét CAD thường trong hộp bé chỉ 1–2 đoạn; chữ bị outline thì uốn lượn nhiều.
  2. Chia trang thành ô 100x100pt. Ô nào có >=25 nét kiểu trên mà KHÔNG có từ nào
     là "mồ côi" — dày đặc hình chữ nhưng không đọc được chữ.

Đo trên 6 bộ bản vẽ thật:
    type1 / type2 / type3 (chữ còn nguyên)      : 0–1 ô mồ côi
    01.DIEN / 02.DIEN NHE / 05.DIEN DH (outline): 23–104 ô ở các trang sơ đồ/bảng

Ngưỡng 10 nằm giữa khoảng trống đó. Chọn thiên về AN TOÀN: thà bỏ sót còn hơn gắn cờ
nhầm một bản vẽ tốt.

GIỚI HẠN đã biết: chỉ bắt được trang có chữ gom thành khối dày (sơ đồ nguyên lý, bảng
tủ điện — cũng chính là nguồn BOQ). Trang MẶT BẰNG có chữ rải rác lẫn trong nét vẽ vẫn
cho điểm thấp và KHÔNG bị gắn cờ. Không nên dùng hàm này như bằng chứng "trang này ổn".
"""
from __future__ import annotations

from collections import Counter

import fitz

_CELL = 100.0            # cạnh ô lưới (point)
_MIN_GLYPHS_PER_CELL = 25
_MIN_SEGMENTS = 6        # số đoạn tối thiểu để coi một nét là hình ký tự
_ORPHAN_CELL_THRESHOLD = 10


def _is_glyph_like(rect: fitz.Rect, items) -> bool:
    if not (0.5 < rect.width < 12 and 1.5 < rect.height < 12):
        return False
    return sum(len(it) - 1 for it in items) >= _MIN_SEGMENTS


def orphan_glyph_cells(page: fitz.Page) -> int:
    """Số ô lưới dày hình-ký-tự nhưng không có chữ đọc được."""
    words: Counter = Counter()
    for w in page.get_text("words"):
        words[(int(w[0] // _CELL), int(w[1] // _CELL))] += 1

    glyphs: Counter = Counter()
    for d in page.get_drawings():
        r = d["rect"]
        if _is_glyph_like(r, d.get("items", [])):
            glyphs[(int(r.x0 // _CELL), int(r.y0 // _CELL))] += 1

    return sum(1 for cell, n in glyphs.items()
               if n >= _MIN_GLYPHS_PER_CELL and words[cell] == 0)


def check(page: fitz.Page) -> dict | None:
    """None nếu trang bình thường; ngược lại trả dict mô tả để đưa vào `debug`."""
    cells = orphan_glyph_cells(page)
    if cells < _ORPHAN_CELL_THRESHOLD:
        return None
    return {
        "reason": "text_outlined",
        "orphanGlyphCells": cells,
        "message": (
            "Trang này đã bị chuyển chữ thành nét vẽ khi xuất PDF nên không đọc được "
            "quy cách cáp, dòng điện aptomat hay tên phụ tải. Cần bản PDF xuất lại "
            "giữ nguyên chữ (hoặc file CAD gốc) thì mới bóc tách được."
        ),
    }
