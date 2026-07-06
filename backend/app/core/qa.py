"""Phase 10 (bản rule-based, chưa cần LLM) - trả lời câu hỏi trên graph.

Hỗ trợ vài mẫu câu phổ biến, dùng chính các quan hệ đã suy ra:
  - "S1 điều khiển đèn nào"      -> controls
  - "P5 thuộc mạch nào / cấp bởi"-> supplies (ngược)
  - "tổng công suất ..."          -> cộng power
Khi tích hợp self-hosted LLM, module này là nơi ghép context graph -> prompt.
"""
from __future__ import annotations

import re

from ..models.graph import AnalysisResult


def answer(result: AnalysisResult, question: str) -> dict:
    q = question.strip()
    ql = q.lower()
    node_by_id = {n.id: n for n in result.nodes}

    # tìm nhãn được nhắc tới (S1, L2, P5, DB-...)
    labels = re.findall(r"\b([A-Z]{1,4}[-/]?[A-Za-z0-9/]*\d[A-Za-z0-9/]*)\b", q)

    # 1) điều khiển / control
    if any(k in ql for k in ["điều khiển", "control", "đèn nào"]):
        for lab in labels:
            targets = _related(result, lab, "controls", node_by_id)
            if targets:
                return _ok(f"{lab} điều khiển: {', '.join(targets)}", targets)
        return _none("Không tìm thấy quan hệ điều khiển cho nhãn trong câu hỏi.")

    # 2) cấp nguồn / supplies
    if any(k in ql for k in ["cấp nguồn", "cấp cho", "supply", "thuộc mạch", "mcb"]):
        for lab in labels:
            targets = _related(result, lab, "supplies", node_by_id)
            if targets:
                return _ok(f"{lab} cấp nguồn cho: {', '.join(targets)}", targets)
            srcs = _related_rev(result, lab, "supplies", node_by_id)
            if srcs:
                return _ok(f"{lab} được cấp nguồn bởi: {', '.join(srcs)}", srcs)
        return _none("Không tìm thấy quan hệ cấp nguồn cho nhãn trong câu hỏi.")

    # 3) tổng công suất
    if "công suất" in ql or "tổng" in ql or "power" in ql:
        total, items = _sum_power(result)
        return _ok(f"Tổng công suất đèn (có ghi W): {total} W ({items} đèn)",
                   [f"{total}W"])

    return _none("Chưa hỗ trợ mẫu câu này (bản rule-based). Có thể bật LLM ở Phase 9.")


def _related(result, label, relation, node_by_id):
    out = []
    for e in result.edges:
        if e.relation != relation:
            continue
        s = node_by_id.get(e.source)
        if s and s.label == label:
            t = node_by_id.get(e.target)
            if t:
                out.append(t.label)
    return sorted(set(out))


def _related_rev(result, label, relation, node_by_id):
    out = []
    for e in result.edges:
        if e.relation != relation:
            continue
        t = node_by_id.get(e.target)
        if t and t.label == label:
            s = node_by_id.get(e.source)
            if s:
                out.append(s.label)
    return sorted(set(out))


def _sum_power(result):
    total, n = 0.0, 0
    for node in result.nodes:
        p = node.attrs.get("power")
        if p:
            m = re.match(r"(\d+(\.\d+)?)", str(p))
            if m:
                total += float(m.group(1))
                n += 1
    return (round(total, 1), n)


def _ok(text, items):
    return {"answer": text, "items": items, "found": True}


def _none(text):
    return {"answer": text, "items": [], "found": False}
