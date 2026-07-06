"""Phase 6 - Rule Engine (KHÔNG dùng AI).

Suy luận quan hệ ngữ nghĩa từ topology 'connected_to':

  Rule 1: Switch  --wire-- Light       => switch CONTROLS light
  Rule 2: DB/Breaker --wire-- Socket   => circuit SUPPLIES socket
  Rule 3: DB/Breaker --wire-- Equipment=> circuit SUPPLIES equipment
  Rule 4: Object gần Room              => object LOCATED_IN room (spatial)

Đầu vào: nodes + connected_to edges của 1 trang (+ rooms).
Đầu ra: danh sách GraphEdge ngữ nghĩa + Relationship (mô tả người đọc được).
"""
from __future__ import annotations

import networkx as nx

from ..models.geometry import Point
from ..models.graph import GraphEdge, GraphNode, Relationship
from ..models.objects import MEPObject

SOURCE_TYPES = {"switch", "distribution_board", "breaker"}


def apply_rules(
    nodes: list[GraphNode],
    conn_edges: list[GraphEdge],
    rooms: list[MEPObject] | None = None,
) -> tuple[list[GraphEdge], list[Relationship]]:
    node_by_id = {n.id: n for n in nodes}
    g = nx.Graph()
    for n in nodes:
        g.add_node(n.id)
    for e in conn_edges:
        if e.relation == "connected_to":
            g.add_edge(e.source, e.target)

    sem_edges: list[GraphEdge] = []
    rels: list[Relationship] = []

    for comp in nx.connected_components(g):
        comp_nodes = [node_by_id[i] for i in comp]
        sources = [n for n in comp_nodes if n.type in SOURCE_TYPES]
        lights = [n for n in comp_nodes if n.type == "light"]
        sockets = [n for n in comp_nodes if n.type == "socket"]
        equip = [n for n in comp_nodes if n.type == "equipment"]

        switches = [n for n in sources if n.type == "switch"]
        feeders = [n for n in sources if n.type in ("distribution_board", "breaker")]

        # Rule 1: switch controls lights
        for sw in switches:
            if lights:
                for lt in lights:
                    sem_edges.append(GraphEdge(
                        source=sw.id, target=lt.id, relation="controls", page=sw.page,
                    ))
                rels.append(Relationship(
                    rule="Rule1", subject=sw.label, relation="controls",
                    objects=[l.label for l in lights],
                    detail=f"Công tắc {sw.label} điều khiển {len(lights)} đèn",
                ))

        # Rule 2 + 3: feeder supplies sockets / equipment
        for fd in feeders:
            targets = sockets + equip
            for t in targets:
                sem_edges.append(GraphEdge(
                    source=fd.id, target=t.id, relation="supplies", page=fd.page,
                ))
            if targets:
                rels.append(Relationship(
                    rule="Rule2/3", subject=fd.label, relation="supplies",
                    objects=[t.label for t in targets],
                    detail=f"{fd.label} cấp nguồn cho {len(targets)} tải",
                ))

    # Rule 4: located_in (spatial) — gắn đối tượng vào phòng gần nhất
    if rooms:
        for n in nodes:
            nearest = _nearest_room(n, rooms)
            if nearest:
                room, dist = nearest
                sem_edges.append(GraphEdge(
                    source=n.id, target=room.id, relation="located_in",
                    page=n.page, weight=round(dist, 1),
                ))

    return sem_edges, rels


def _nearest_room(node: GraphNode, rooms: list[MEPObject], max_dist: float = 350.0):
    p = Point(x=node.x, y=node.y)
    best, best_d = None, max_dist
    for r in rooms:
        if r.page != node.page:
            continue
        d = p.dist(r.position)
        if d < best_d:
            best, best_d = r, d
    return (best, best_d) if best else None
