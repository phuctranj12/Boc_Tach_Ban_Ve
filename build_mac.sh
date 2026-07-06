#!/usr/bin/env bash
# Build bản macOS (để TEST cơ chế đóng gói trên máy này; .exe phải build trên Windows).
set -e
cd "$(dirname "$0")"

echo "[1/3] Build giao diện (frontend)..."
cd frontend && npm install >/dev/null 2>&1 && npm run build && cd ..

echo "[2/3] Cài PyInstaller..."
source .venv/bin/activate
pip install -q pyinstaller

echo "[3/3] Đóng gói..."
cd backend && pyinstaller --noconfirm mep_reader.spec && cd ..

echo "Xong! File: backend/dist/MEP-Drawing-Reader"
