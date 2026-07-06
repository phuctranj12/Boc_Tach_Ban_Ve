"""Orchestrator: chạy Phase 1 -> 7 và tổng hợp AnalysisResult.

Phase 7 (Cross Sheet Linking) ở mức nhẹ: nối các đối tượng cùng nhãn xuất hiện
trên nhiều trang khác nhau bằng quan hệ 'cross_ref' (vd L1 trên layout & trên
single line diagram là cùng một mạch).
"""
from __future__ import annotations

from collections import defaultdict

from ..models.graph import AnalysisResult, GraphEdge, GraphNode, Relationship
from .graph_builder import build_graph
from .object_extractor import extract_objects, extract_rooms
from .pdf_parser import parse_pdf
from .rule_engine import apply_rules
from .sheet_classifier import classify_sheet


def _sheet_summary(sheet) -> dict:
    """Bản rút gọn của Sheet để trả về client (không kèm raw drawings)."""
    type_counts: dict[str, int] = defaultdict(int)
    for o in sheet.objects:
        type_counts[o.type.value] += 1
    return {
        "page": sheet.page,
        "sheet_no": sheet.sheet_no,
        "sheet_type": sheet.sheet_type.value,
        "title": sheet.title,
        "width": sheet.width,
        "height": sheet.height,
        "object_count": len(sheet.objects),
        "object_counts": dict(type_counts),
        "drawing_count": len(sheet.drawings),
        "wire_segments": sum(1 for d in sheet.drawings if d.group == "wire"),
        "top_layers": dict(list(sheet.layers.items())[:12]),
        "classify_score": sheet.classify_score,
    }


def run_pipeline(pdf_path: str, job_id: str, filename: str) -> AnalysisResult:
    sheets = parse_pdf(pdf_path)

    all_nodes: list[GraphNode] = []
    all_conn: list[GraphEdge] = []
    all_sem: list[GraphEdge] = []
    all_rels: list[Relationship] = []
    sheet_summaries: list[dict] = []

    for sheet in sheets:
        classify_sheet(sheet)
        extract_objects(sheet)
        rooms = extract_rooms(sheet)

        nodes, conn_edges = build_graph(sheet)
        sem_edges, rels = apply_rules(nodes, conn_edges, rooms)

        all_nodes.extend(nodes)
        all_conn.extend(conn_edges)
        all_sem.extend(sem_edges)
        all_rels.extend(rels)
        sheet_summaries.append(_sheet_summary(sheet))

    # --- Phase 7: cross-sheet linking theo nhãn ---
    cross_edges = _cross_sheet_links(all_nodes)

    edges = all_conn + all_sem + cross_edges

    stats = {
        "pages": len(sheets),
        "nodes": len(all_nodes),
        "connected_to": len(all_conn),
        "semantic_edges": len(all_sem),
        "cross_ref": len(cross_edges),
        "relationships": len(all_rels),
        "by_type": _count_by(all_nodes, lambda n: n.type),
        "by_sheet_type": _count_by(sheet_summaries, lambda s: s["sheet_type"]),
    }

    return AnalysisResult(
        job_id=job_id,
        filename=filename,
        page_count=len(sheets),
        sheets=sheet_summaries,
        nodes=all_nodes,
        edges=edges,
        relationships=all_rels,
        stats=stats,
    )


def _cross_sheet_links(nodes: list[GraphNode]) -> list[GraphEdge]:
    by_label: dict[tuple[str, str], list[GraphNode]] = defaultdict(list)
    for n in nodes:
        by_label[(n.label, n.type)].append(n)
    edges: list[GraphEdge] = []
    for group in by_label.values():
        pages = {n.page for n in group}
        if len(pages) < 2:
            continue
        # nối node đầu tiên của mỗi trang thành chuỗi tham chiếu
        rep_per_page = {}
        for n in group:
            rep_per_page.setdefault(n.page, n)
        reps = list(rep_per_page.values())
        for a, b in zip(reps, reps[1:]):
            edges.append(GraphEdge(
                source=a.id, target=b.id, relation="cross_ref",
                attrs={"label": a.label},
            ))
    return edges


def _count_by(items, key):
    out: dict[str, int] = defaultdict(int)
    for it in items:
        out[key(it)] += 1
    return dict(out)
