"""Đối tượng MEP đã chuẩn hoá (Phase 3) + dữ liệu thô từ Phase 1."""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from .geometry import BBox, Point


# ---------- Dữ liệu thô Phase 1 ----------
class RawWord(BaseModel):
    text: str
    bbox: BBox


class RawDrawing(BaseModel):
    """Một nét vẽ vector, đã được làm phẳng thành các đoạn thẳng."""
    layer: str
    group: str = ""
    points: list[Point]  # chuỗi điểm tạo polyline/line


# ---------- Đối tượng chuẩn hoá Phase 3 ----------
class ObjectType(str, Enum):
    switch = "switch"
    light = "light"
    socket = "socket"
    distribution_board = "distribution_board"
    breaker = "breaker"
    equipment = "equipment"
    room = "room"
    unknown = "unknown"


class MEPObject(BaseModel):
    id: str                         # ví dụ "p1.S1" (page + label) để duy nhất toàn dự án
    label: str                      # nhãn gốc trên bản vẽ: S1, L1, P5...
    type: ObjectType
    page: int
    sheet_no: Optional[str] = None
    position: Point
    bbox: Optional[BBox] = None
    layer: Optional[str] = None
    attrs: dict = Field(default_factory=dict)  # power, rating... suy ra thêm
