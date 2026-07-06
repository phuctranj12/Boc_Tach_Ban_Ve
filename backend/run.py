"""Khởi động backend chỉ với 1 lệnh:  python run.py

Chạy FastAPI (app.main:app) bằng uvicorn. Có thể đổi host/port/reload qua biến
môi trường: HOST, PORT, RELOAD.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Đảm bảo import được package 'app' dù chạy từ bất kỳ thư mục nào.
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    reload = os.getenv("RELOAD", "1") not in ("0", "false", "False")

    print(f"🔌 MEP Drawing Reader API → http://localhost:{port}  (docs: /docs)")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
