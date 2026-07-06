#!/usr/bin/env bash
# Khởi động backend FastAPI (cổng 8000)
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate
cd backend
exec uvicorn app.main:app --reload --port 8000
