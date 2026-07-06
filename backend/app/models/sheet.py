"""Model cho sheet và kết quả parse từng trang."""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from .objects import RawWord, RawDrawing, MEPObject


class SheetType(str, Enum):
    lighting_layout = "lighting_layout"
    power_layout = "power_layout"
    single_line = "single_line"
    schedule = "schedule"
    panel_schedule = "panel_schedule"
    legend = "legend"
    mechanical = "mechanical"
    plumbing = "plumbing"
    electrical_layout = "electrical_layout"  # power + lighting trên cùng 1 sheet
    floor_plan = "floor_plan"
    unknown = "unknown"


class Sheet(BaseModel):
    page: int
    sheet_no: Optional[str] = None
    sheet_type: SheetType = SheetType.unknown
    title: Optional[str] = None
    width: float
    height: float
    classify_score: dict[str, int] = Field(default_factory=dict)

    # dữ liệu trích xuất (không serialize ra client nếu quá lớn — tuỳ route)
    words: list[RawWord] = Field(default_factory=list)
    drawings: list[RawDrawing] = Field(default_factory=list)
    objects: list[MEPObject] = Field(default_factory=list)
    layers: dict[str, int] = Field(default_factory=dict)  # tên layer -> số nét
