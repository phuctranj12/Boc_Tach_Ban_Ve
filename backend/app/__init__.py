"""Bóc tách bản vẽ MEP (HAWEE).

Khi cài qua pip, package này có tên `boc_tach_ban_ve` (trong repo là `app`).

    from boc_tach_ban_ve import analyze_pdf, answer
    result = analyze_pdf("ban_ve.pdf")
    print(result.stats)
    print(answer(result, "DB-1 cấp nguồn cho những gì?"))

Các tên dưới đây được import lười (lazy): `import boc_tach_ban_ve` không kéo
theo PyMuPDF / FastAPI cho tới khi thật sự dùng.
"""
from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

__version__ = "0.1.1"

if TYPE_CHECKING:
    from .models.graph import AnalysisResult

__all__ = [
    "__version__",
    "analyze_pdf",
    "run_pipeline",
    "answer",
    "AnalysisResult",
    "create_app",
    "build_mcp",
]


def analyze_pdf(pdf_path: str | os.PathLike[str], job_id: str | None = None) -> "AnalysisResult":
    """Chạy toàn bộ pipeline trên 1 file PDF, không lưu gì xuống đĩa."""
    from .core.pipeline import run_pipeline

    path = os.fspath(pdf_path)
    return run_pipeline(path, job_id or uuid.uuid4().hex, os.path.basename(path))


def create_app():
    """Trả về FastAPI app đầy đủ (API + /mcp + sheet-config) để mount/chạy."""
    from .main import app

    return app


def __getattr__(name: str):
    if name == "run_pipeline":
        from .core.pipeline import run_pipeline

        return run_pipeline
    if name == "answer":
        from .core.qa import answer

        return answer
    if name == "AnalysisResult":
        from .models.graph import AnalysisResult

        return AnalysisResult
    if name == "build_mcp":
        from .mcp_server import build_mcp

        return build_mcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
