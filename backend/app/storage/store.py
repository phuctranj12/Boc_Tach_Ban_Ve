"""Object/Result Store đơn giản: lưu kết quả ra JSON file + cache RAM.

Đủ cho giai đoạn chưa cần Postgres/Neo4j. Có thể thay bằng DB sau mà không
đổi interface.
"""
from __future__ import annotations

import json
from typing import Optional

from ..config import RESULT_DIR
from ..models.graph import AnalysisResult

_CACHE: dict[str, AnalysisResult] = {}


def save_result(result: AnalysisResult) -> None:
    _CACHE[result.job_id] = result
    path = RESULT_DIR / f"{result.job_id}.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def get_result(job_id: str) -> Optional[AnalysisResult]:
    if job_id in _CACHE:
        return _CACHE[job_id]
    path = RESULT_DIR / f"{job_id}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        result = AnalysisResult(**data)
        _CACHE[job_id] = result
        return result
    return None


def list_results() -> list[dict]:
    out = []
    for path in sorted(RESULT_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            out.append({
                "job_id": data.get("job_id"),
                "filename": data.get("filename"),
                "page_count": data.get("page_count"),
                "stats": data.get("stats", {}),
            })
        except Exception:
            continue
    return out
