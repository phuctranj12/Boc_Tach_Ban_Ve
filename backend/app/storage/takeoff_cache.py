"""Cache kết quả bóc tách TỰ ĐỘNG (chưa sửa tay) theo trang — LƯU XUỐNG ĐĨA.

Bóc 1 trang tốn ~2-4s nên ta lưu lại để restart backend không phải bóc lại.
Khác với review_store (dữ liệu người dùng đã sửa/xác nhận), đây là bản bóc gốc.

Mỗi job 1 file: data/takeoff/{job_id}.json
    {"job_id": "...", "pages": {"0": <payload>, "1": <payload>, ...}}
"""
from __future__ import annotations

import json
import os

from ..config import DATA_DIR

TAKEOFF_DIR = DATA_DIR / "takeoff"
TAKEOFF_DIR.mkdir(parents=True, exist_ok=True)


def _path(job_id: str):
    return TAKEOFF_DIR / f"{job_id}.json"


def _load(job_id: str) -> dict:
    p = _path(job_id)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"job_id": job_id, "pages": {}}


def _save(data: dict) -> None:
    # Ghi ra file tạm rồi đổi tên (atomic) để prewarm chạy nền không làm hỏng file
    # khi đang có request đọc cùng lúc.
    p = _path(data["job_id"])
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def get_job(job_id: str) -> dict[str, dict]:
    """Tất cả trang đã bóc của job (str(page) -> payload)."""
    return _load(job_id)["pages"]


def get_page(job_id: str, page: int) -> dict | None:
    return _load(job_id)["pages"].get(str(page))


def save_page(job_id: str, page: int, payload: dict) -> None:
    data = _load(job_id)
    data["pages"][str(page)] = payload
    _save(data)
