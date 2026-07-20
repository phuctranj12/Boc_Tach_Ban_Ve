"""Lưu dữ liệu bóc tách ĐÃ SỬA/XÁC NHẬN theo từng trang (human-in-the-loop).

Mỗi job có 1 file JSON: data/reviews/{job_id}.json
    {
      "job_id": "...",
      "pages": {
        "0": {"page":0,"diagramType":"panel_table","panelName":"...",
              "items":[{...}], "confirmed":true, "updatedAt":"..."},
        ...
      }
    }
Tách riêng với kết quả bóc tự động để người dùng chỉnh tay mà không mất bản gốc.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from ..config import DATA_DIR
from ..core.takeoff.sheet_meta import normalize_meta

REVIEW_DIR = DATA_DIR / "reviews"
REVIEW_DIR.mkdir(parents=True, exist_ok=True)


def _path(job_id: str):
    return REVIEW_DIR / f"{job_id}.json"


def _load(job_id: str) -> dict:
    p = _path(job_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"job_id": job_id, "pages": {}}


def _save(data: dict) -> None:
    _path(data["job_id"]).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_page(job_id: str, page: int) -> dict | None:
    rec = _load(job_id)["pages"].get(str(page))
    if rec is not None:
        # Bản ghi lưu trước khi có tính năng này chưa có 'meta' -> bù khoá rỗng.
        rec["meta"] = normalize_meta(rec.get("meta"))
    return rec


def save_page(job_id: str, page: int, payload: dict) -> dict:
    data = _load(job_id)
    record = {
        "page": page,
        "diagramType": payload.get("diagramType", ""),
        "panelName": payload.get("panelName", ""),
        "panels": payload.get("panels", []),     # tủ tổng (name/power/ptt/kdt)
        # Thông tin hành chính người dùng xem/sửa được. Chuẩn hoá để luôn đủ 5 khoá
        # kể cả khi client gửi thiếu — JSON xuất ra phải luôn có các trường này.
        "meta": normalize_meta(payload.get("meta")),
        "items": payload.get("items", []),
        "confirmed": bool(payload.get("confirmed", False)),
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    data["pages"][str(page)] = record
    _save(data)
    return record


def get_all(job_id: str) -> dict:
    return _load(job_id)


def status(job_id: str) -> list[dict]:
    """Tóm tắt trạng thái duyệt từng trang."""
    data = _load(job_id)
    out = []
    for k, v in sorted(data["pages"].items(), key=lambda kv: int(kv[0])):
        out.append({
            "page": v["page"],
            "diagramType": v.get("diagramType", ""),
            "panelName": v.get("panelName", ""),
            "count": len(v.get("items", [])),
            "confirmed": v.get("confirmed", False),
            "updatedAt": v.get("updatedAt"),
        })
    return out
