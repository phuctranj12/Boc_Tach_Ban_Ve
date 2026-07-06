#!/usr/bin/env bash
# Khởi động 1 dự án (backend + frontend) trên bộ cổng riêng, để chạy NHIỀU dự án
# song song mà không trùng cổng.
#
# Cách dùng:
#   ./run_project.sh            # dự án 0: backend 8000, frontend 5173
#   ./run_project.sh 1          # dự án 1: backend 8001, frontend 5174
#   ./run_project.sh 2          # dự án 2: backend 8002, frontend 5175
#   BACKEND_PORT=9000 FRONTEND_PORT=6000 ./run_project.sh   # chỉ định tay
#
# Mỗi dự án nên là 1 BẢN SAO thư mục riêng (data/ tách biệt). Nhấn Ctrl+C để tắt cả 2.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SLOT="${1:-0}"

export BACKEND_PORT="${BACKEND_PORT:-$((8000 + SLOT))}"
export FRONTEND_PORT="${FRONTEND_PORT:-$((5173 + SLOT))}"
export PORT="$BACKEND_PORT"   # backend/run.py đọc biến PORT

echo "=================================================="
echo "  Dự án slot $SLOT"
echo "  Backend  : http://localhost:$BACKEND_PORT   (docs: /docs)"
echo "  Frontend : http://localhost:$FRONTEND_PORT"
echo "  Ctrl+C để tắt cả hai"
echo "=================================================="

# Tắt cả backend lẫn frontend khi thoát.
pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Backend: ưu tiên venv của dự án nếu có.
PY="python3"
[ -x "$ROOT/.venv/bin/python" ] && PY="$ROOT/.venv/bin/python"
( cd "$ROOT/backend" && PORT="$BACKEND_PORT" "$PY" run.py ) &
pids+=($!)

# Frontend: vite đọc BACKEND_PORT/FRONTEND_PORT từ môi trường.
( cd "$ROOT/frontend" && BACKEND_PORT="$BACKEND_PORT" FRONTEND_PORT="$FRONTEND_PORT" npm run dev ) &
pids+=($!)

wait
