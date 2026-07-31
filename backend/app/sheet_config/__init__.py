"""Sheet Configure — module độc lập, ở nhờ chung image với luồng bóc tách bản vẽ."""
from pathlib import Path

from .router import router
from .version import __version__

# Giao diện web đã build (Vite, base=/json-to-sheet/). Là artifact sinh tự động
# từ repo json-to-sheet — cách cập nhật xem README.md cùng thư mục.
SHEET_CONFIG_WEB = Path(__file__).resolve().parent / "web"

__all__ = ["router", "SHEET_CONFIG_WEB", "__version__"]
