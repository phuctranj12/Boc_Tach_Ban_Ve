"""Khởi chạy ứng dụng đóng gói: chạy server + tự mở trình duyệt.

Đây là entry point cho bản đóng gói (PyInstaller). Double-click file thực thi:
  1. Tìm 1 cổng trống.
  2. Mở trình duyệt mặc định tới giao diện.
  3. Chạy uvicorn (server) cho tới khi đóng cửa sổ.
"""
from __future__ import annotations

import functools
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# In ra ngay lập tức (không buffer) để cửa sổ console hiện link kịp thời.
print = functools.partial(print, flush=True)  # noqa: A001

# Cho phép import package 'app' dù chạy từ bất kỳ đâu (kể cả khi đã đóng gói).
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _free_port(preferred: int = 8000) -> int:
    """Dùng cổng ưa thích nếu trống, không thì xin cổng trống bất kỳ."""
    for port in (preferred, 0):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", port))
            p = s.getsockname()[1]
            s.close()
            return p
        except OSError:
            continue
    return preferred


def main() -> None:
    import uvicorn
    from app.main import app

    # Cho phép ép cổng qua biến môi trường PORT (mặc định 8000, tự né nếu bận).
    env_port = os.getenv("PORT")
    port = int(env_port) if env_port else _free_port(8000)
    url = f"http://127.0.0.1:{port}"

    # Ghi link ra file cạnh ứng dụng để dễ tìm lại nếu lỡ tắt trình duyệt.
    try:
        from app.config import APP_HOME
        (APP_HOME / "MO_UNG_DUNG.txt").write_text(
            f"Mở trình duyệt và vào: {url}\n", encoding="utf-8"
        )
    except Exception:
        pass

    def _open():
        time.sleep(1.5)  # chờ server sẵn sàng
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()

    print("=" * 56)
    print("  MEP Drawing Reader đang chạy")
    print(f"  Mở trình duyệt tại: {url}")
    print("  (Đừng đóng cửa sổ này khi đang dùng ứng dụng)")
    print("=" * 56)

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
