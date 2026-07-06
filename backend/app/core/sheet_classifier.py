"""Phase 2 - Sheet Classification.

Phân loại dựa trên TIÊU ĐỀ trong title block (góc dưới-phải) thay vì đếm
toàn bộ text — vì legend/ký hiệu lặp lại trên mọi sheet nên đếm full-text
gây nhiễu (mọi trang đều ra power_layout).

Quy trình:
  1. Lấy mã sheet (E-C2-417...) từ toàn trang.
  2. Ghép text trong vùng title block -> dò tiêu đề chức năng.
  3. Tính điểm theo SHEET_KEYWORDS trên tiêu đề; xử lý trường hợp kết hợp
     (POWER + LIGHTING -> electrical_layout).
Không dùng AI.
"""
from __future__ import annotations

import re

from ..config import SHEET_KEYWORDS, TITLE_BLOCK_REGION
from ..models.sheet import Sheet, SheetType

_SHEET_NO_RE = re.compile(r"\b([A-Z]{1,3}-[A-Z0-9]{1,4}-\d{2,4})\b")
# Các cụm tiêu đề thường gặp để hiển thị (ưu tiên tiếng Anh)
_TITLE_PHRASES = [
    "POWER SUPPLY AND LIGHTING LAYOUT", "LIGHTING LAYOUT", "POWER LAYOUT",
    "WATER SUPPLY LAYOUT", "DRAINAGE LAYOUT", "SINGLE LINE DIAGRAM",
    "PANEL SCHEDULE", "MECHANICAL LAYOUT", "VENTILATION LAYOUT",
]


def _title_block_text(sheet: Sheet) -> str:
    x1r, y1r, x2r, y2r = TITLE_BLOCK_REGION
    W, H = sheet.width, sheet.height
    xmin, ymin, xmax, ymax = x1r * W, y1r * H, x2r * W, y2r * H
    parts = []
    for w in sheet.words:
        c = w.bbox.center
        if xmin <= c.x <= xmax and ymin <= c.y <= ymax:
            parts.append(w.text)
    return " ".join(parts).upper()


def _extract_sheet_no(text: str) -> str | None:
    m = _SHEET_NO_RE.search(text)
    return m.group(1) if m else None


def classify_sheet(sheet: Sheet) -> Sheet:
    full_text = " ".join(w.text for w in sheet.words).upper()
    title_text = _title_block_text(sheet)
    sheet.sheet_no = _extract_sheet_no(full_text)

    # tiêu đề hiển thị
    for phrase in _TITLE_PHRASES:
        if phrase in title_text:
            sheet.title = phrase.title()
            break

    # Tín hiệu từ title block là QUYẾT ĐỊNH; full_text chỉ dùng khi title trống.
    title_scores = {k: 0 for k in SHEET_KEYWORDS}
    full_scores = {k: 0 for k in SHEET_KEYWORDS}
    for stype, keywords in SHEET_KEYWORDS.items():
        for kw in keywords:
            if kw in title_text:
                title_scores[stype] += 1
            if kw in full_text:
                full_scores[stype] += 1

    scores = title_scores if any(title_scores.values()) else full_scores

    has_power = scores["power_layout"] > 0
    has_light = scores["lighting_layout"] > 0
    has_water = scores["plumbing"] > 0

    if has_water and not (title_scores["power_layout"] or title_scores["lighting_layout"]):
        sheet.sheet_type = SheetType.plumbing
    elif has_power and has_light:
        sheet.sheet_type = SheetType.electrical_layout
    else:
        best_type, best_score = max(scores.items(), key=lambda kv: kv[1])
        sheet.sheet_type = SheetType(best_type) if best_score > 0 else SheetType.floor_plan

    if not sheet.title:
        sheet.title = sheet.sheet_no
    sheet.classify_score = {k: v for k, v in scores.items() if v > 0}
    return sheet
