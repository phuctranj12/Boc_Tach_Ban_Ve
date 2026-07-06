"""Phase 3 - Object Extraction.

Sinh các MEPObject chuẩn hoá từ text words + layer.

Chiến lược:
  - Mỗi word khớp một LABEL_PATTERN -> tạo object (vị trí = tâm bbox).
  - Suy ra thuộc tính phụ:
      * light: công suất (vd "9W") nếu có word dạng số+W gần đó.
      * breaker: rating từ chính nhãn (1P-10A).
  - Phòng (room): nhận diện theo từ điển tên phòng tiếng Việt.
"""
from __future__ import annotations

import re

from ..config import LABEL_PATTERNS
from ..models.geometry import Point
from ..models.objects import MEPObject, ObjectType
from ..models.sheet import Sheet

_COMPILED = [(t, re.compile(p)) for t, p in LABEL_PATTERNS]
_POWER_RE = re.compile(r"^\d+(\.\d+)?W$", re.IGNORECASE)
_RATING_RE = re.compile(r"(\d+P)-(\d+)A")

# Tên phòng thường gặp (tiếng Việt) — dùng cho located_in
ROOM_KEYWORDS = {
    "KHÁCH": "Phòng khách",
    "BẾP": "Bếp",
    "NGỦ": "Phòng ngủ",
    "WC": "WC",
    "BAN": "Ban công",
    "GIẶT": "Phòng giặt",
    "ĂN": "Phòng ăn",
}


def _match_type(text: str) -> str | None:
    for otype, rx in _COMPILED:
        if rx.match(text):
            return otype
    return None


def _nearest_power(center: Point, sheet: Sheet, max_dist: float = 35.0) -> str | None:
    best, best_d = None, max_dist
    for w in sheet.words:
        if _POWER_RE.match(w.text):
            d = center.dist(w.bbox.center)
            if d < best_d:
                best, best_d = w.text.upper(), d
    return best


def extract_objects(sheet: Sheet) -> Sheet:
    objects: list[MEPObject] = []
    seen: set[tuple[str, int, int]] = set()  # tránh trùng (label tại cùng vị trí)

    for w in sheet.words:
        text = w.text.strip()
        otype = _match_type(text)
        if not otype:
            continue
        center = w.bbox.center
        key = (text, round(center.x / 5), round(center.y / 5))
        if key in seen:
            continue
        seen.add(key)

        obj = MEPObject(
            id=f"p{sheet.page}.{text}",
            label=text,
            type=ObjectType(otype),
            page=sheet.page,
            sheet_no=sheet.sheet_no,
            position=center,
            bbox=w.bbox,
        )

        if otype == "light":
            p = _nearest_power(center, sheet)
            if p:
                obj.attrs["power"] = p
        elif otype == "breaker":
            m = _RATING_RE.search(text)
            if m:
                obj.attrs["poles"] = m.group(1)
                obj.attrs["rating"] = f"{m.group(2)}A"

        objects.append(obj)

    sheet.objects = objects
    return sheet


def extract_rooms(sheet: Sheet) -> list[MEPObject]:
    """Tách các nhãn phòng để dùng cho quan hệ located_in (Phase 6/8)."""
    rooms: list[MEPObject] = []
    for w in sheet.words:
        up = w.text.upper()
        for kw, name in ROOM_KEYWORDS.items():
            if kw in up:
                rooms.append(MEPObject(
                    id=f"p{sheet.page}.room.{w.text}",
                    label=name,
                    type=ObjectType.room,
                    page=sheet.page,
                    sheet_no=sheet.sheet_no,
                    position=w.bbox.center,
                    bbox=w.bbox,
                ))
                break
    return rooms
