"""Router Sheet Configure — chuẩn hoá cấu hình bộ bản vẽ shop (JSON/JSONC).

Hoàn toàn tách biệt với luồng bóc tách bản vẽ: prefix riêng, không dùng chung
storage, không import gì từ `app.core`. Ở chung image chỉ để tận dụng một chỗ
deploy duy nhất.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from . import runner
from .version import __version__

router = APIRouter(prefix="/api/sheet-config", tags=["sheet-config"])

_MEDIA_TYPE = "application/json; charset=utf-8"


def _passthrough(status: int, body: str) -> Response:
    """Trả nguyên trạng thứ gói JavaScript quyết định, không diễn giải lại."""
    return Response(content=body, status_code=status, media_type=_MEDIA_TYPE)


def _unavailable(error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"ok": False, "error": str(error)},
    )


async def _forward(method: str, target: str, request: Request | None = None) -> Response:
    body = b""
    headers: dict[str, str] = {}

    if request is not None:
        body = await request.body()
        if len(body) > runner.MAX_BODY_BYTES:
            return JSONResponse(status_code=413, content={"ok": False, "error": "Body vượt quá 2 MB."})
        content_type = request.headers.get("content-type")
        if content_type:
            headers["content-type"] = content_type

    try:
        status, payload = await runner.call(method, target, body=body, headers=headers, version=__version__)
    except runner.SheetConfigUnavailable as error:
        return _unavailable(error)

    return _passthrough(status, payload)


@router.get("/health")
async def health() -> Response:
    """Sức khoẻ của riêng module này, kèm chẩn đoán Node."""
    info = runner.availability()
    if not info["ready"]:
        return JSONResponse(status_code=503, content={"ok": False, "service": "sheet-config", **info})
    return await _forward("GET", "/api/health")


@router.get("/template")
async def template() -> Response:
    """Cấu hình mẫu để client dựng form ban đầu."""
    return await _forward("GET", "/api/template")


@router.post("/normalize")
async def normalize(request: Request) -> Response:
    """JSONC thô -> JSON chuẩn + cảnh báo + thống kê.

    Query hỗ trợ: `strict=1` coi mọi cảnh báo là lỗi, `pretty=0` xuất một dòng.
    """
    return await _forward("POST", f"/api/normalize?{request.url.query}", request)


@router.post("/validate")
async def validate(request: Request) -> Response:
    """Chỉ kiểm tra luật trên một cấu hình đã có."""
    return await _forward("POST", "/api/validate", request)
