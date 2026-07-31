"""Cầu nối sang logic Sheet Configure (viết bằng JavaScript).

Module này CỐ TÌNH không chứa một chút logic nghiệp vụ nào. Toàn bộ việc đọc
JSONC, chuẩn hoá cấu hình, kiểm tra luật và quyết định mã trạng thái đều nằm
trong `js/api-cli.mjs`. Ở đây chỉ gọi tiến trình Node rồi chuyển tiếp nguyên
trạng những gì nó trả về.

Lý do: bản web của Sheet Configure chạy chính đoạn JavaScript đó ngay trong
trình duyệt. Nếu viết lại bằng Python thì sẽ có hai bản logic phải giữ đồng bộ
mãi mãi, và chỉ cần lệch một chi tiết nhỏ (ví dụ JavaScript in số 51.0 thành
51 còn Python in thành 51.0) là file cấu hình xuất ra đã khác nhau.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

_JS_ENTRY = Path(__file__).resolve().parent / "js" / "api-cli.mjs"

# Chặn sớm ở tầng Python để một request khổng lồ không kịp làm phồng bộ nhớ
# rồi mới bị Node từ chối. Đây là hàng rào tài nguyên, không phải luật nghiệp
# vụ — ngưỡng thật vẫn do MAX_BODY_BYTES bên JavaScript quyết định.
MAX_BODY_BYTES = 2 * 1024 * 1024

_TIMEOUT_SECONDS = 20


class SheetConfigUnavailable(RuntimeError):
    """Không tìm thấy Node hoặc gói JavaScript đi kèm."""


def node_executable() -> str | None:
    return shutil.which("node")


def availability() -> dict:
    """Thông tin chẩn đoán, dùng cho endpoint health."""
    node = node_executable()
    return {
        "node": node,
        "bundle": str(_JS_ENTRY),
        "bundle_exists": _JS_ENTRY.is_file(),
        "ready": bool(node) and _JS_ENTRY.is_file(),
    }


async def call(method: str, target: str, body: bytes = b"", headers: dict | None = None,
               version: str = "unknown") -> tuple[int, str]:
    """Gọi một endpoint của Sheet Configure, trả về (status_code, body_json).

    `target` là đường dẫn nội bộ của gói JavaScript, ví dụ "/api/normalize"
    kèm query string nếu có.
    """
    node = node_executable()
    if not node:
        raise SheetConfigUnavailable(
            "Không tìm thấy Node trong image. Dockerfile phải copy binary node "
            "từ stage frontend sang runtime."
        )
    if not _JS_ENTRY.is_file():
        raise SheetConfigUnavailable(f"Thiếu gói JavaScript tại {_JS_ENTRY}.")

    process = await asyncio.create_subprocess_exec(
        node, str(_JS_ENTRY), method, target, json.dumps(headers or {}), version,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(body), timeout=_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.wait()
        raise SheetConfigUnavailable("Xử lý cấu hình quá lâu, đã huỷ.") from exc

    if not stdout:
        detail = stderr.decode("utf-8", "replace").strip()[:500]
        raise SheetConfigUnavailable(f"Tiến trình Node không trả về gì. stderr: {detail}")

    payload = json.loads(stdout.decode("utf-8"))
    return int(payload["status"]), payload["body"]
