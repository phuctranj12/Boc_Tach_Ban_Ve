"""KIỂU A — Busbar + vạch chéo "/".

Bọc lại logic trong core/sld_extractor.py (đã kiểm chứng khớp 100% trên bản vẽ
loại 1) và trả về TakeoffResult thống nhất với các extractor khác.
"""
from __future__ import annotations

import fitz

from .base import TakeoffItem, TakeoffResult, collect_vertical_lines
from ..sld_extractor import extract_sld as _legacy_extract, _SPEC_RE


def detect_score(page: fitz.Page) -> float:
    """Điểm khả năng là Kiểu A: đếm cột mô tả cáp dạng '2x1C ...'."""
    return sum(1 for v in collect_vertical_lines(page) if _SPEC_RE.match(v.text))


def extract(page: fitz.Page, page_index: int) -> TakeoffResult:
    legacy = _legacy_extract(page, page_index)
    res = TakeoffResult(page=page_index, diagram_type="busbar_slash",
                        panel_name=legacy.panel_name)
    for it in legacy.items:
        res.items.append(TakeoffItem(
            panelName=it.get("panelName", ""),
            roadName=it.get("roadName", ""),
            loadName=it.get("loadName", ""),
            size=it.get("size", ""),
            cableSpec=it.get("cableSpec", ""),
            conduit=it.get("conduit", ""),
        ))
    res.debug = legacy.debug
    return res
