"""Cache kết quả parse text của PyMuPDF theo TỪNG TRANG.

Parse text là phần tốn nhất của pipeline bóc tách: `get_text("dict")` trên một
trang A3 ~62k nét mất ~2.6s. Trong khi đó một lượt `extract_takeoff` đụng vào
cùng một trang tới 8-9 lần: `detect_type` cho cả 4 extractor chấm điểm (mỗi cái
tự gọi collect_*), rồi extractor thắng cuộc bóc lại từ đầu.

Cache được gắn THẲNG LÊN OBJECT TRANG, không dùng dict toàn cục khoá theo
`id(page.parent)`: `orient.rotate_page` tạo Document tạm rồi `.close()` ngay, nên
CPython có thể cấp lại cùng địa chỉ cho doc tạm kế tiếp — khoá theo `id()` sẽ trả
nhầm nội dung của trang xoay này cho trang xoay khác. Gắn lên Page thì vòng đời
cache khớp đúng vòng đời trang: không va chạm, không rò rỉ, không cần LRU.

Chỉ cache dữ liệu THÔ từ PyMuPDF. Các list dẫn xuất (TextItem…) vẫn được dựng lại
mỗi lần gọi để người dùng hàm không vô tình chia sẻ/sửa chung một list.
"""
from __future__ import annotations

import fitz

_CACHE_ATTR = "_page_text_cache"


def _cache(page: fitz.Page) -> dict:
    c = getattr(page, _CACHE_ATTR, None)
    if c is None:
        c = {}
        setattr(page, _CACHE_ATTR, c)
    return c


def text_dict(page: fitz.Page) -> dict:
    """`page.get_text("dict")`, parse tối đa 1 lần cho mỗi trang."""
    c = _cache(page)
    if "dict" not in c:
        c["dict"] = page.get_text("dict")
    return c["dict"]


def text_words(page: fitz.Page) -> list:
    """`page.get_text("words")`, parse tối đa 1 lần cho mỗi trang."""
    c = _cache(page)
    if "words" not in c:
        c["words"] = page.get_text("words")
    return c["words"]
