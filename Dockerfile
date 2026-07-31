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

# Hugging Face Spaces chạy container bằng user UID 1000 (không phải root). Tạo sẵn
# user này và cấp quyền để app ghi được thư mục data/ (upload, kết quả). Không có
# bước này thì upload trên HF sẽ lỗi "Permission denied".
RUN useradd -m -u 1000 user

WORKDIR /app

# Thư viện Python (cài dưới quyền root trước khi đổi user).
# pymupdf dùng wheel self-contained (không cần lib hệ thống). Nếu về sau `import fitz`
# lỗi thiếu lib, thêm: RUN apt-get update && apt-get install -y --no-install-recommends libgl1
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# Runtime Node cho module Sheet Configure (backend/app/sheet_config). Logic của
# module đó viết bằng JavaScript và dùng chung y nguyên với bản web chạy trên
# trình duyệt, nên gọi Node thay vì chép lại sang Python — tránh hai bản lệch nhau.
# node:20-slim và python:3.12-slim cùng nền Debian bookworm nên binary chạy được
# trực tiếp, không cần cài thêm thư viện hệ thống nào.
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node

# Mã nguồn backend + giao diện đã build, sở hữu bởi 'user' để ghi được data/.
# Giữ đúng layout /app/backend + /app/frontend/dist để main.py resolve:
#   Path(__file__).parents[2] / "frontend" / "dist" == /app/frontend/dist
COPY --chown=user:user backend/ /app/backend/
COPY --chown=user:user --from=frontend /frontend/dist /app/frontend/dist

# Đổi chủ TOÀN BỘ /app sang 'user' (kể cả thư mục /app/backend do bước cài đặt tạo ra
# dưới quyền root) để app tạo/ghi được data/ khi chạy bằng UID 1000 trên HF.
RUN chown -R user:user /app

USER user
WORKDIR /app/backend

# Nền tảng cloud (Render/Railway) inject $PORT; mặc định 8000 khi chạy tay.
# 2 worker để chịu vài người test song song (analyze chạy đồng bộ, chặn event loop);
# cache đĩa (takeoff_cache) chia sẻ nên nhiều worker không xung đột.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
