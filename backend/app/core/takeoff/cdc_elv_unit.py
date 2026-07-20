"""Kiểu D — sơ đồ tủ điện nhẹ căn hộ (bộ hồ sơ CDC, file "02.DIEN NHE").

Đây là loại trang DUY NHẤT trong bộ hồ sơ CDC còn giữ chữ thật: 9 trang
"BỐ TRÍ ĐIỆN NHẸ CĂN HỘ CH01…CH30". Các trang còn lại đã bị convert chữ thành nét khi
xuất PDF (xem `outlined_text.py`) nên không bóc được.

Cấu trúc trang — mỗi tuyến cáp là một dòng dạng SỐ LƯỢNG + LOẠI CÁP, phòng đích nằm
ngay bên phải cùng hàng:

    1x CÁP UTP 4P-0.5 Cat6        PHÒNG KHÁCH
    1x CÁP UTP 4P-0.5 Cat6        PHÒNG NGỦ 1
    1x CÁP QUANG SINGLEMODE 2FO   (không có phòng — là cáp trục)
    (ỐNG PVC D20)
    4x CÁP UTP 4P-0.5 Cat6        (không có phòng — là cáp trục)

Dòng KHÔNG có phòng đích là tuyến TRỤC từ tủ tầng vào căn hộ. Quan sát trên cả 9 trang:
số lượng của tuyến trục UTP luôn bằng đúng tổng số dòng nhánh (4 phòng ↔ "4x",
1 phòng ↔ "1x"). Tính chất này được dùng làm KIỂM TRA CHÉO trong `debug` — lệch thì
gần như chắc chắn đã bóc sót hoặc bắt nhầm một dòng.
"""
from __future__ import annotations

import re

import fitz

from .base import TakeoffItem, TakeoffResult, parse_size
from ..page_text import text_dict

# "1x CÁP UTP 4P-0.5 Cat6", "4x CÁP UTP…", "1x CÁP QUANG SINGLEMODE 2FO"
_QTY_CABLE_RE = re.compile(r"^(\d+)\s*x\s*(CÁP\s+.+)$", re.IGNORECASE)
# "(ỐNG PVC D20)" — ống luồn, in ở dòng ngay dưới cùng cột
_CONDUIT_RE = re.compile(r"^\(\s*(ỐNG\s+[^)]+)\)$", re.IGNORECASE)
# Mã căn hộ trong tiêu đề bảng: "CHI TIẾT TỦ ĐIỆN NHẸ CĂN HỘ CH01"
_UNIT_RE = re.compile(r"CĂN\s+HỘ\s+(CH\d+[A-Z]?)", re.IGNORECASE)

_ROW_TOL = 14.0        # sai số hàng khi dóng phòng đích với dòng cáp
_CONDUIT_MAX_DY = 20.0  # ống luồn nằm ngay dưới dòng cáp
_CONDUIT_MAX_DX = 30.0

# Khung tên chiếm góc phải-dưới; bỏ qua để không bắt nhầm chữ hành chính.
_TITLE_BLOCK = (0.75, 0.55)


def _body_lines(page: fitz.Page) -> list[tuple[float, float, float, str]]:
    """(y, x0, x1, text) của text NGOÀI khung tên."""
    W, H = page.rect.width, page.rect.height
    out = []
    for b in text_dict(page)["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"]).strip()
            bb = l["bbox"]
            if t and not (bb[0] > _TITLE_BLOCK[0] * W and bb[1] > _TITLE_BLOCK[1] * H):
                out.append((bb[1], bb[0], bb[2], t))
    out.sort()
    return out


def detect_score(page: fitz.Page) -> float:
    return float(sum(1 for _, _, _, t in _body_lines(page) if _QTY_CABLE_RE.match(t)))


def _destination(rows, y: float, x1: float) -> str:
    """Nhãn phòng đích: text gần nhất bên PHẢI, cùng hàng, không phải dòng cáp."""
    best, best_dx = "", None
    for y2, x2, _x2b, t2 in rows:
        if abs(y2 - y) > _ROW_TOL or x2 <= x1 or _QTY_CABLE_RE.match(t2):
            continue
        dx = x2 - x1
        if best_dx is None or dx < best_dx:
            best, best_dx = t2, dx
    return best


def _conduit_by_spec(rows) -> dict[str, str]:
    """Bảng tra {loại cáp -> ống luồn}.

    Ống luồn KHÔNG in cạnh từng dòng callout mà ở phần chú thích, ngay DƯỚI dòng ghi
    tên loại cáp (không có tiền tố số lượng). Trên cả 9 trang căn hộ, "(ỐNG PVC D20)"
    luôn nằm dưới "CÁP QUANG SINGLEMODE 2FO". Nên tra theo TÊN CÁP, không theo vị trí
    dòng callout — callout có thể cách chú thích cả trăm point.
    """
    out: dict[str, str] = {}
    for i, (y, x0, _x1, t) in enumerate(rows):
        m = _CONDUIT_RE.match(t)
        if not m:
            continue
        for y2, x2, _x2b, t2 in rows[:i][::-1]:
            if 0 < y - y2 <= _CONDUIT_MAX_DY and abs(x2 - x0) <= _CONDUIT_MAX_DX \
                    and "CÁP" in t2.upper():
                out[_norm(t2)] = m.group(1).strip()
                break
    return out


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().upper()


def extract(page: fitz.Page, page_index: int) -> TakeoffResult:
    rows = _body_lines(page)
    res = TakeoffResult(page=page_index, diagram_type="cdc_elv_unit")

    unit = ""
    for _, _, _, t in rows:
        m = _UNIT_RE.search(t)
        if m:
            unit = m.group(1).upper()
            break
    res.panel_name = f"Tủ điện nhẹ căn hộ {unit}".strip() if unit else "Tủ điện nhẹ căn hộ"

    conduits = _conduit_by_spec(rows)
    n_branch = 0
    trunk_qty = 0
    for y, x0, x1, t in rows:
        m = _QTY_CABLE_RE.match(t)
        if not m:
            continue
        qty = int(m.group(1))
        spec = re.sub(r"\s+", " ", m.group(2)).strip()
        dest = _destination(rows, y, x1)
        if dest:
            n_branch += 1
        elif "UTP" in spec.upper():
            trunk_qty = max(trunk_qty, qty)

        res.items.append(TakeoffItem(
            panelName=res.panel_name,
            roadName=dest or "Trục",
            # Không có phòng đích => tuyến trục từ tủ tầng vào căn hộ.
            loadName=dest or "Tuyến trục từ tủ tầng đến căn hộ",
            size=parse_size(spec),      # cáp điện nhẹ không ghi mm2 -> thường rỗng
            cableSpec=spec,
            conduit=conduits.get(_norm(spec), ""),
            itemGroup="Cáp điện nhẹ",
            itemName="Cáp tín hiệu (UTP/quang)",
            qty=qty,
        ))

    res.debug = {
        "unit": unit,
        "branches": n_branch,
        "trunkQty": trunk_qty,
        # Cáp trục UTP phải bằng đúng tổng số nhánh — lệch là dấu hiệu bóc sai.
        "trunkMatchesBranches": (trunk_qty == n_branch) if trunk_qty else None,
    }
    return res
