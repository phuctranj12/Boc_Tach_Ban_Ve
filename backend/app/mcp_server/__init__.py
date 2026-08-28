"""Lớp MCP — để Claude (Desktop / Code / connector) gọi thẳng các chức năng.

KHÔNG có xác thực: endpoint /mcp mở như phần còn lại của Space (auth: none).
Toàn bộ lớp OAuth 2.1 trong khung `HUONG_DAN_TICH_HOP_MCP_SERVER.md` được cố ý
bỏ qua vì tool này không cần bảo mật.

Kết nối:
  Claude Code : claude mcp add --transport http boc-tach https://<host>/mcp
  claude.ai   : Settings -> Connectors -> Add custom connector -> https://<host>/mcp
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .tools import register_tools

_INSTRUCTIONS = """\
Bộ công cụ bóc tách bản vẽ MEP của HAWEE.

Luồng thường dùng:
  1. analyze_pdf(pdf_url=...)      -> nhận job_id
  2. get_boq(job_id)              -> BOQ khối lượng cáp/ống toàn dự án
Hoặc extract_page(job_id, page)   -> bóc tách 1 trang.
ask_drawing(job_id, question)     -> hỏi quan hệ điều khiển/cấp nguồn.

Nhóm normalize_sheet_config / validate_sheet_config / get_sheet_config_template
là luồng ĐỘC LẬP: chuẩn hoá file cấu hình bộ bản vẽ shop (DocumentSetConfig),
không liên quan tới bóc tách.

Lưu ý: Space miễn phí ngủ khi lâu không dùng — lần gọi đầu có thể mất 20-60s.
job_id chỉ sống trong phiên, mất khi Space restart.
"""


def build_mcp() -> FastMCP:
    # Space chạy sau reverse proxy của Hugging Face với Host là tên miền thật, nên
    # lớp chống DNS-rebinding của SDK (mặc định chỉ cho Host localhost) sẽ trả 421.
    # Tool này public và không có gì để bảo vệ -> tắt hẳn. Nếu muốn siết lại, đặt
    # MCP_ALLOWED_HOSTS="host1,host2" và bật lại enable_dns_rebinding_protection.
    allowed = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=bool(allowed),
        allowed_hosts=allowed or ["*"],
        allowed_origins=["*"],
    )

    mcp = FastMCP(
        "boc-tach-ban-ve",
        instructions=_INSTRUCTIONS,
        stateless_http=True,          # Dockerfile chạy 2 worker -> không giữ session
        streamable_http_path="/",     # sẽ mount ở "/mcp"
        transport_security=transport_security,
    )
    register_tools(mcp)
    return mcp


__all__ = ["build_mcp"]
