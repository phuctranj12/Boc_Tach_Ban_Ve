"""Phase 1 - PDF Parsing bằng PyMuPDF.

Trích từ mỗi trang:
  - Text words (get_text("words"))  -> RawWord
  - Drawings (get_drawings())       -> RawDrawing (đã làm phẳng về polyline)
  - Layer của từng nét vẽ (drawing['layer'])
  - Kích thước trang

KHÔNG OCR, KHÔNG vision. Toàn bộ dữ liệu là vector thật.
"""
from __future__ import annotations

import fitz  # PyMuPDF

from ..models.geometry import BBox, Point
from ..models.objects import RawWord, RawDrawing
from ..models.sheet import Sheet
from .layer_filter import clean_layer_name, classify_layer


def _flatten_items(items) -> list[list[Point]]:
    """Chuyển 'items' của một drawing thành danh sách polyline (list điểm)."""
    polylines: list[list[Point]] = []
    for it in items:
        op = it[0]
        if op == "l":  # line: ('l', p1, p2)
            p1, p2 = it[1], it[2]
            polylines.append([Point(x=p1.x, y=p1.y), Point(x=p2.x, y=p2.y)])
        elif op == "re":  # rectangle: ('re', Rect, ...)
            r = it[1]
            polylines.append([
                Point(x=r.x0, y=r.y0), Point(x=r.x1, y=r.y0),
                Point(x=r.x1, y=r.y1), Point(x=r.x0, y=r.y1),
                Point(x=r.x0, y=r.y0),
            ])
        elif op == "qu":  # quad: ('qu', Quad)
            q = it[1]
            polylines.append([
                Point(x=q.ul.x, y=q.ul.y), Point(x=q.ur.x, y=q.ur.y),
                Point(x=q.lr.x, y=q.lr.y), Point(x=q.ll.x, y=q.ll.y),
                Point(x=q.ul.x, y=q.ul.y),
            ])
        elif op == "c":  # bezier curve: lấy 2 đầu mút (đủ cho topology dây)
            p1, p4 = it[1], it[4]
            polylines.append([Point(x=p1.x, y=p1.y), Point(x=p4.x, y=p4.y)])
    return polylines


def parse_page(page: fitz.Page, page_index: int) -> Sheet:
    rect = page.rect
    sheet = Sheet(page=page_index, width=rect.width, height=rect.height)

    # --- Words ---
    for w in page.get_text("words"):
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
        if text.strip():
            sheet.words.append(RawWord(text=text, bbox=BBox(x1=x0, y1=y0, x2=x1, y2=y1)))

    # --- Drawings + layers ---
    layer_count: dict[str, int] = {}
    for d in page.get_drawings():
        raw_layer = d.get("layer") or ""
        clean = clean_layer_name(raw_layer)
        group = classify_layer(raw_layer)
        for poly in _flatten_items(d.get("items", [])):
            if len(poly) < 2:
                continue
            sheet.drawings.append(RawDrawing(layer=clean, group=group, points=poly))
        layer_count[clean] = layer_count.get(clean, 0) + 1

    sheet.layers = dict(sorted(layer_count.items(), key=lambda kv: -kv[1]))
    return sheet


def parse_pdf(path: str) -> list[Sheet]:
    """Parse toàn bộ file PDF -> danh sách Sheet (chưa phân loại/extract)."""
    doc = fitz.open(path)
    sheets: list[Sheet] = []
    try:
        for i in range(doc.page_count):
            sheets.append(parse_page(doc[i], i))
    finally:
        doc.close()
    return sheets
