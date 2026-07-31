"""Điểm vào FastAPI."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .sheet_config import SHEET_CONFIG_WEB, router as sheet_config_router

app = FastAPI(
    title="MEP Drawing Reader",
    description="Đọc bản vẽ MEP bằng Vector + Graph + Rule Engine.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Sheet Configure: luồng độc lập, chỉ ở nhờ chung image. Phải đăng ký trước
# catch-all SPA bên dưới, nếu không mọi /api/sheet-config/* sẽ rơi vào index.html.
app.include_router(sheet_config_router)

# Giao diện web của Sheet Configure tại /json-to-sheet. Bản build dùng base riêng
# nên asset của nó nằm ở /json-to-sheet/assets, không đụng /assets của giao diện
# bóc tách. Cũng phải mount trước catch-all SPA bên dưới.
if SHEET_CONFIG_WEB.is_dir():

    # Mount chỉ khớp khi có dấu / cuối. Không có route này thì "/json-to-sheet"
    # rơi xuống catch-all SPA bên dưới và trả về giao diện bóc tách. Cơ chế tự
    # thêm dấu / của Starlette không cứu được, vì catch-all đã khớp trước.
    @app.get("/json-to-sheet", include_in_schema=False)
    def _sheet_config_web_slash():
        return RedirectResponse("/json-to-sheet/")

    app.mount(
        "/json-to-sheet",
        StaticFiles(directory=SHEET_CONFIG_WEB, html=True),
        name="sheet-config-web",
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "mep-drawing-reader"}


# --- Phục vụ giao diện đã build (production / đóng gói) ---
# Khi đóng gói (PyInstaller): frontend/dist được nhúng vào thư mục tạm (_MEIPASS)
# dưới tên 'frontend_dist'. Khi chạy thường: trỏ tới frontend/dist trong repo.
if getattr(sys, "frozen", False):
    _DIST = Path(sys._MEIPASS) / "frontend_dist"  # type: ignore[attr-defined]
else:
    _DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/")
    def _index():
        return FileResponse(_DIST / "index.html")

    @app.get("/{path:path}")
    def _spa(path: str):
        """SPA fallback: đường dẫn không phải /api -> trả file tĩnh hoặc index.html."""
        f = _DIST / path
        if f.is_file():
            return FileResponse(f)
        return FileResponse(_DIST / "index.html")
