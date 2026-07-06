"""Phase 5 - Graph Builder.

Xây topology THẬT từ vector:
  1. Lấy các đoạn dây (drawings group == 'wire').
  2. Snap 2 đầu mỗi đoạn về lưới (WIRE_SNAP_TOLERANCE) -> nút mạng dây.
  3. Dùng NetworkX nối các nút mạng -> các thành phần liên thông (mạng dây rời nhau).
  4. Gắn mỗi đối tượng MEP vào nút mạng gần nhất (<= OBJECT_ATTACH_TOLERANCE).
  5. Các đối tượng cùng một thành phần liên thông => "connected_to" (nối thành chuỗi
     theo hàng xóm gần nhất, giống S1-L1-L2-L3).

Trả về (nodes, edges) cho 1 trang.
"""
from __future__ import annotations

import networkx as nx

from ..config import OBJECT_ATTACH_TOLERANCE, WIRE_SNAP_TOLERANCE, MIN_WIRE_LENGTH
from ..models.geometry import Point
from ..models.graph import GraphEdge, GraphNode
from ..models.objects import MEPObject
from ..models.sheet import Sheet


def _snap(p: Point, tol: float) -> tuple[int, int]:
    return (round(p.x / tol), round(p.y / tol))


def _build_wire_network(sheet: Sheet) -> nx.Graph:
    """Đồ thị các nút mạng dây (key = toạ độ đã snap)."""
    g = nx.Graph()
    for d in sheet.drawings:
        if d.group != "wire":
            continue
        pts = d.points
        for a, b in zip(pts, pts[1:]):
            if a.dist(b) < MIN_WIRE_LENGTH:
                continue
            ka, kb = _snap(a, WIRE_SNAP_TOLERANCE), _snap(b, WIRE_SNAP_TOLERANCE)
            g.add_node(ka, x=a.x, y=a.y)
            g.add_node(kb, x=b.x, y=b.y)
            if ka != kb:
                g.add_edge(ka, kb)
    return g


def _nearest_wire_node(obj: MEPObject, wire_g: nx.Graph):
    """Tìm nút mạng dây gần đối tượng nhất trong ngưỡng. None nếu không có."""
    best, best_d = None, OBJECT_ATTACH_TOLERANCE
    ox, oy = obj.position.x, obj.position.y
    for n, data in wire_g.nodes(data=True):
        d = ((data["x"] - ox) ** 2 + (data["y"] - oy) ** 2) ** 0.5
        if d < best_d:
            best, best_d = n, d
    return best


def build_graph(sheet: Sheet) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes: list[GraphNode] = [
        GraphNode(
            id=o.id, label=o.label, type=o.type.value, page=o.page,
            sheet_no=o.sheet_no, x=o.position.x, y=o.position.y, attrs=o.attrs,
        )
        for o in sheet.objects
    ]
    edges: list[GraphEdge] = []
    if not sheet.objects:
        return nodes, edges

    wire_g = _build_wire_network(sheet)
    if wire_g.number_of_nodes() == 0:
        return nodes, edges

    # map: component-id -> list các (object, wire_node)
    comp_of = {}
    for i, comp in enumerate(nx.connected_components(wire_g)):
        for n in comp:
            comp_of[n] = i

    buckets: dict[int, list[MEPObject]] = {}
    for o in sheet.objects:
        wn = _nearest_wire_node(o, wire_g)
        if wn is None:
            continue
        cid = comp_of.get(wn)
        if cid is None:
            continue
        buckets.setdefault(cid, []).append(o)

    # Trong mỗi thành phần: nối các đối tượng theo chuỗi hàng xóm gần nhất
    for objs in buckets.values():
        if len(objs) < 2:
            continue
        edges.extend(_chain_edges(objs, sheet.page))

    return nodes, edges


def _chain_edges(objs: list[MEPObject], page: int) -> list[GraphEdge]:
    """Nối các đối tượng thành 1 chuỗi (nearest-neighbor path)."""
    remaining = objs[:]
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]
        nxt = min(remaining, key=lambda o: o.position.dist(last.position))
        ordered.append(nxt)
        remaining.remove(nxt)
    out = []
    for a, b in zip(ordered, ordered[1:]):
        out.append(GraphEdge(
            source=a.id, target=b.id, relation="connected_to", page=page,
            weight=round(a.position.dist(b.position), 1),
        ))
    return out
