"""Knowledge graph: node, edge và kết quả phân tích tổng (Phase 5/6/8)."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    page: int
    sheet_no: Optional[str] = None
    x: float
    y: float
    attrs: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str            # connected_to / controls / supplies / located_in
    page: Optional[int] = None
    weight: float = 1.0
    attrs: dict = Field(default_factory=dict)


class Relationship(BaseModel):
    """Kết quả Rule Engine ở dạng dễ đọc cho người."""
    rule: str
    subject: str
    relation: str
    objects: list[str]
    detail: str = ""


class AnalysisResult(BaseModel):
    job_id: str
    filename: str
    page_count: int
    sheets: list = Field(default_factory=list)          # list[Sheet] (rút gọn)
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)
