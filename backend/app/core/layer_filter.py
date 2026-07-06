"""Phase 4 - Layer Filtering.

Map tên layer CAD (lấy từ PyMuPDF drawing['layer']) về nhóm chức năng:
wire / light / switch / socket / equipment / text / other.

Tên layer trong PDF có dạng nested xobject, ví dụ:
    "4821 - UNIT LAYOUT 2BR(+) - TYPE B$0$A-WALL"
    "4813 - UNIT LAYOUT 2BR(+) - TYPE B|S-COLS"
Phần CAD layer thật là đoạn sau dấu '$0$' hoặc '|' cuối cùng.
"""
from __future__ import annotations

from ..config import LAYER_GROUPS


def clean_layer_name(raw: str | None) -> str:
    """Lấy tên layer CAD gọn từ chuỗi xobject lồng nhau."""
    if not raw:
        return ""
    name = raw
    for sep in ("$0$", "|"):
        if sep in name:
            name = name.split(sep)[-1]
    return name.strip()


def classify_layer(raw: str | None) -> str:
    """Trả về nhóm chức năng của layer. 'other' nếu không khớp.

    Phân loại trên TÊN LAYER ĐÃ LÀM SẠCH (vd 'E-Line', 'E-PO WIRING') để tránh
    nhiễu từ phần block-name của xobject path (vd 'UNIT LAYOUT ... MEP').
    """
    upper = clean_layer_name(raw).upper()
    if not upper:
        return "other"
    # Ưu tiên các nhóm cụ thể trước (wire trước socket vì 'E-PO WIRING' vs 'E-PO')
    order = ["wire", "switch", "light", "socket", "equipment", "text"]
    for group in order:
        for token in LAYER_GROUPS[group]:
            if token.upper() in upper:
                return group
    return "other"


def filter_by_group(drawings, group: str):
    """Lọc danh sách RawDrawing theo nhóm chức năng."""
    return [d for d in drawings if d.group == group]
