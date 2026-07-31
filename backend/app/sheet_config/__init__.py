"""Sheet Configure — module độc lập, ở nhờ chung image với luồng bóc tách bản vẽ."""
from .router import router

from .version import __version__
__all__ = ["router", "__version__"]
