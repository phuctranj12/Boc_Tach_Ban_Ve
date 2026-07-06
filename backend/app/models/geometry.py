"""Kiểu hình học cơ bản dùng chung."""
from __future__ import annotations

import math
from pydantic import BaseModel


class Point(BaseModel):
    x: float
    y: float

    def dist(self, other: "Point") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> Point:
        return Point(x=(self.x1 + self.x2) / 2, y=(self.y1 + self.y2) / 2)

    @property
    def width(self) -> float:
        return abs(self.x2 - self.x1)

    @property
    def height(self) -> float:
        return abs(self.y2 - self.y1)

    @classmethod
    def from_seq(cls, seq) -> "BBox":
        return cls(x1=seq[0], y1=seq[1], x2=seq[2], y2=seq[3])


class Segment(BaseModel):
    """Một đoạn dây/đường thẳng đã trích từ vector PDF."""
    start: Point
    end: Point
    layer: str = ""
    group: str = ""  # nhóm chức năng sau khi lọc layer (wire/light/...)

    @property
    def length(self) -> float:
        return self.start.dist(self.end)
