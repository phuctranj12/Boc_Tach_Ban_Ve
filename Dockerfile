# syntax=docker/dockerfile:1
# ============================================================================
# MEP Drawing Reader — image chạy cả API (FastAPI) lẫn giao diện trong 1 process.
# Backend phục vụ luôn frontend đã build (same-origin) nên không dính CORS/host.
# ============================================================================

# ---- Stage 1: build giao diện React (Vite) ----
FROM node:20-slim AS frontend
WORKDIR /frontend
# Cài dependency trước (tận dụng cache lớp) rồi mới build.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # -> /frontend/dist

# ---- Stage 2: runtime Python ----
# BẮT BUỘC Python 3.12 (không 3.14) vì pydantic-core.
FROM python:3.12-slim AS runtime

# Không ghi .pyc, log không buffer để thấy ngay trên console cloud.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RELOAD=0

WORKDIR /app

# Thư viện Python. pymupdf dùng wheel self-contained (không cần lib hệ thống).
# Nếu về sau `import fitz` lỗi thiếu lib, thêm: RUN apt-get update && apt-get install -y --no-install-recommends libgl1
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# Mã nguồn backend + giao diện đã build.
# Giữ đúng layout /app/backend + /app/frontend/dist để main.py resolve:
#   Path(__file__).parents[2] / "frontend" / "dist" == /app/frontend/dist
COPY backend/ /app/backend/
COPY --from=frontend /frontend/dist /app/frontend/dist

WORKDIR /app/backend

# Nền tảng cloud (Render/Railway) inject $PORT; mặc định 8000 khi chạy tay.
# 2 worker để chịu vài người test song song (analyze chạy đồng bộ, chặn event loop);
# cache đĩa (takeoff_cache) chia sẻ nên nhiều worker không xung đột.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
