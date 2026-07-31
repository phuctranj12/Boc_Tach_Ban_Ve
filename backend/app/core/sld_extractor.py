"""Bóc tách CÁP & ỐNG LUỒN từ Sơ đồ nguyên lý tủ điện (Single Line Diagram).

KIỂU A — Busbar + vạch chéo "/":
  - Có danh sách CÁP (text dọc, bắt đầu "2x1C ...") + ỐNG ("ỐNG PVC ...") ở góc trái.
  - Mỗi loại cáp tương ứng MỘT đường ngang (horizontal route) ở một mức y riêng,
    điểm bắt đầu (x trái) trùng với cột text mô tả cáp đó.
  - Mỗi TẢI có 1 đường dọc thả xuống; tại chỗ nó cắt 1 đường cáp ngang có 1 VẠCH CHÉO "/"
    → đường cáp đó chính là cáp của tải.
  - TERMINAL (L1, S1, P1, ... SPARE) nằm trên 1 hàng; tải gán về terminal gần nhất theo x.

Đây là bóc tách VECTOR tất định (không AI, không Vision). Mọi ngưỡng nằm trong
SLD_CFG để dễ tinh chỉnh khi gặp bản vẽ trình bày hơi khác.

Module độc lập, có thể tái dùng cho các sơ đồ nguyên lý ở mọi trang. Đầu ra là
list[dict] đúng schema bóc tách khối lượng (QS).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import fitz

from .page_text import text_dict, text_words

# ----- ngưỡng cấu hình (point) -----
# ĐO TRÊN BẢN VẼ CHUẨN (types/type1.pdf, chữ cao 7.67pt). Bản vẽ xuất ở tỷ lệ khác —
# nhất là khi tách riêng 1 tủ sang khổ giấy riêng — thì mọi khoảng cách đổi theo, nên
# lúc dùng phải nhân với `_page_scale(page)`. Không làm vậy thì phóng to 2x là vạch
# chéo dài quá `slash_len_range`, không nhận được vạch nào và TOÀN BỘ dòng mất quy
# cách cáp (vẫn ra đủ dòng nên hỏng câm). Riêng ngưỡng GÓC thì bất biến tỷ lệ.
_BASE_TEXT_H = 7.67

SLD_CFG = {
    "terminal_row_tol": 8,       # gộp các nhãn terminal cùng 1 hàng
    "route_min_len": 60,         # đường cáp ngang tối thiểu
    "route_angle_tol": 8,        # độ lệch để coi là ngang
    "route_y_merge": 4,          # gộp các đoạn ngang cùng mức y
    "slash_len_range": (5, 16),  # độ dài vạch chéo
    "slash_angle_range": (25, 65),  # góc vạch chéo so với phương ngang (|ang| hoặc 180-ang)
    "spec_match_x_tol": 18,      # khớp đường cáp với cột text spec theo x
    "slash_match_x_tol": 16,     # khớp vạch chéo với cột tải theo x
    # 70 chứ không phải 60: trên type1 tải SPARE cách terminal 59.1px — sát ngưỡng
    # cũ chỉ 1.5%, nên chỉ cần ước lượng tỷ lệ lệch vài % là mất terminal. Terminal
    # kế tiếp cách 125.8px (xa gấp 2.1 lần) nên nới tới 70 vẫn không nhập nhằng.
    "load_terminal_x_tol": 70,   # gán tải về terminal theo x
    "load_col_merge_x": 14,      # gộp 2 dòng Việt/Anh cùng cột thành 1 tải
}

_TERMINAL_RE = re.compile(r"^(?:L|S|P|C)\d+$|^SPARE$", re.IGNORECASE)
_SPEC_RE = re.compile(r"^2x1C", re.IGNORECASE)
_CONDUIT_RE = re.compile(r"^ỐNG|^ONG|^PVC", re.IGNORECASE)
_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*mm2", re.IGNORECASE)
_PANEL_RE = re.compile(r"^(?:DB|MDB|SDB|TĐ|MSB)[-/].+", re.IGNORECASE)


# ---------- cấu trúc trung gian ----------
@dataclass
class TextItem:
    text: str
    x: float
    y: float
    vertical: bool = False


@dataclass
class CableRoute:
    y: float
    x_start: float
    x_end: float
    size: str = ""
    cable_spec: str = ""
    conduit: str = ""


@dataclass
class SLDResult:
    page: int
    panel_name: str = ""
    cables: list[CableRoute] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    debug: dict = field(default_factory=dict)


def _page_scale(page: fitz.Page) -> float:
    """Tỷ lệ plot của trang so với bản vẽ chuẩn (theo chiều cao chữ trung vị)."""
    # Import trễ: takeoff/__init__ → busbar_slash → module này, import ở đầu file
    # sẽ thành vòng tròn.
    from .takeoff.base import text_scale
    th = text_scale(page)
    if not th:
        return 1.0
    return min(6.0, max(0.25, th / _BASE_TEXT_H))


# ---------- trích text & line ----------
def _collect_texts(page: fitz.Page) -> tuple[list[TextItem], list[TextItem]]:
    """Trả về (horizontal_words, vertical_lines)."""
    words = [
        TextItem(w[4].strip(), (w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
        for w in text_words(page) if w[4].strip()
    ]
    verticals: list[TextItem] = []
    for b in text_dict(page)["blocks"]:
        for l in b.get("lines", []):
            d = l.get("dir", (1, 0))
            if abs(d[0]) < 0.5:  # text dọc
                txt = "".join(s["text"] for s in l["spans"]).strip()
                if txt:
                    bb = l["bbox"]
                    verticals.append(TextItem(txt, (bb[0] + bb[2]) / 2, bb[3], vertical=True))
    return words, verticals


def _collect_segments(page: fitz.Page):
    segs = []
    for dr in page.get_drawings():
        for it in dr.get("items", []):
            if it[0] == "l":
                a, b = it[1], it[2]
                segs.append((a.x, a.y, b.x, b.y))
            elif it[0] == "re":
                r = it[1]
                segs.append((r.x0, r.y0, r.x1, r.y0))
                segs.append((r.x0, r.y1, r.x1, r.y1))
    return segs


# ---------- xác định vùng SLD ----------
def _find_sld_region(words, verticals, s: float):
    """Vùng SLD = quanh các cột cáp '2x1C' và hàng terminal. Trả bbox (x1,y1,x2,y2)."""
    specs = [v for v in verticals if _SPEC_RE.match(v.text)]
    terms = [w for w in words if _TERMINAL_RE.match(w.text)]
    if not specs or not terms:
        return None
    # hàng terminal phổ biến nhất (nhiều nhãn cùng y nhất)
    ys = {}
    for t in terms:
        key = round(t.y / (6 * s))
        ys.setdefault(key, []).append(t)
    term_row = max(ys.values(), key=len)
    term_y = sum(t.y for t in term_row) / len(term_row)
    x1 = min(s2.x for s2 in specs) - 40 * s
    x2 = max(t.x for t in term_row) + 120 * s
    y1 = term_y - 220 * s
    y2 = max(s2.y for s2 in specs) + 40 * s
    return (x1, y1, x2, y2), term_row, term_y


# ---------- ghép cáp ----------
def _build_cable_routes(segs, verticals, region, s: float):
    (x1, y1, x2, y2) = region
    # đường ngang dài trong dải giữa terminal & tải
    horiz = []
    for sx, sy, ex, ey in segs:
        if max(sy, ey) > y2 or min(sy, ey) < y1:
            continue
        dx, dy = ex - sx, ey - sy
        L = math.hypot(dx, dy)
        if L < SLD_CFG["route_min_len"] * s:
            continue
        ang = abs(math.degrees(math.atan2(dy, dx)))
        if ang < SLD_CFG["route_angle_tol"] or ang > 180 - SLD_CFG["route_angle_tol"]:
            horiz.append((min(sx, ex), max(sx, ex), (sy + ey) / 2, L))
    # gộp theo mức y
    horiz.sort(key=lambda h: h[2])
    routes: list[CableRoute] = []
    for xs, xe, y, L in horiz:
        merged = False
        for r in routes:
            if abs(r.y - y) <= SLD_CFG["route_y_merge"] * s:
                r.x_start = min(r.x_start, xs)
                r.x_end = max(r.x_end, xe)
                merged = True
                break
        if not merged:
            routes.append(CableRoute(y=y, x_start=xs, x_end=xe))

    # gắn spec + conduit cho từng route theo x_start
    specs = [v for v in verticals if _SPEC_RE.match(v.text)]
    conduits = [v for v in verticals if _CONDUIT_RE.match(v.text)]
    for r in routes:
        spec = _nearest(specs, r.x_start, SLD_CFG["spec_match_x_tol"] * 3 * s)
        if spec:
            r.cable_spec = spec.text
            m = _SIZE_RE.search(spec.text)
            if m:
                r.size = f"{m.group(1)}mm2"
            cond = _nearest(conduits, spec.x, 40 * s)
            if cond:
                r.conduit = cond.text
    # chỉ giữ route có spec (loại bỏ đường khung/busbar)
    return [r for r in routes if r.cable_spec]


def _nearest(items, x, tol):
    best, bd = None, tol
    for it in items:
        d = abs(it.x - x)
        if d < bd:
            best, bd = it, d
    return best


# ---------- vạch chéo ----------
def _find_slashes(segs, routes, region, s: float):
    (x1, y1, x2, y2) = region
    route_ys = [r.y for r in routes]
    lo, hi = (v * s for v in SLD_CFG["slash_len_range"])
    amin, amax = SLD_CFG["slash_angle_range"]
    slashes = []  # (mx, route_index)
    for sx, sy, ex, ey in segs:
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        if my > y2 or my < y1 or mx < x1 or mx > x2:
            continue
        dx, dy = ex - sx, ey - sy
        L = math.hypot(dx, dy)
        if not (lo <= L <= hi):
            continue
        ang = abs(math.degrees(math.atan2(dy, dx)))
        ang = min(ang, 180 - ang)
        if not (amin <= ang <= amax):
            continue
        # vạch chéo phải nằm trên 1 mức cáp (không phải mũi tên ở đỉnh tải)
        ri = _nearest_route_index(my, route_ys, tol=5 * s)
        if ri is not None:
            slashes.append((mx, ri))
    return slashes


def _nearest_route_index(y, route_ys, tol):
    best, bd = None, tol
    for i, ry in enumerate(route_ys):
        d = abs(ry - y)
        if d < bd:
            best, bd = i, d
    return best


# ---------- pipeline chính ----------
def extract_sld(page: fitz.Page, page_index: int) -> SLDResult:
    words, verticals = _collect_texts(page)
    res = SLDResult(page=page_index)

    s = _page_scale(page)
    region_info = _find_sld_region(words, verticals, s)
    if not region_info:
        res.debug["error"] = "Không tìm thấy vùng SLD (thiếu cột cáp '2x1C' hoặc terminal)."
        return res
    region, term_row, term_y = region_info
    x1, y1, x2, y2 = region

    segs = _collect_segments(page)
    # đường cáp chỉ nằm DƯỚI hàng terminal (loại busbar phía trên)
    cable_band = (x1, term_y + 3 * s, x2, y2)
    routes = _build_cable_routes(segs, verticals, cable_band, s)
    res.cables = routes
    if not routes:
        res.debug["error"] = "Không dựng được đường cáp ngang."
        return res

    slashes = _find_slashes(segs, routes, region, s)

    # panel name (DB-...) gần góc trên-trái vùng SLD
    panels = [w for w in words if _PANEL_RE.match(w.text) and y1 - 60 * s <= w.y <= term_y]
    if panels:
        res.panel_name = min(panels, key=lambda w: w.x).text

    # các TẢI = text dọc nằm dưới hàng terminal, không phải cột cáp
    cable_xs = [v.x for v in verticals if _SPEC_RE.match(v.text) or _CONDUIT_RE.match(v.text)]
    loads = []
    for v in verticals:
        if _SPEC_RE.match(v.text) or _CONDUIT_RE.match(v.text):
            continue
        if v.x < x1 or v.x > x2 or v.y < term_y:
            continue
        if cable_xs and min(abs(v.x - cx) for cx in cable_xs) < 20 * s:
            continue
        loads.append(v)
    # gộp 2 dòng (Việt/Anh) cùng cột thành 1 tải
    loads = _merge_load_columns(loads, SLD_CFG["load_col_merge_x"] * s)

    terms = sorted(term_row, key=lambda t: t.x)
    for ld in loads:
        # cáp: vạch chéo gần cột tải nhất
        size = spec = conduit = ""
        cand = [(abs(mx - ld.x), ri) for mx, ri in slashes
                if abs(mx - ld.x) <= SLD_CFG["slash_match_x_tol"] * s]
        if cand:
            ri = min(cand)[1]
            r = routes[ri]
            size, spec, conduit = r.size, r.cable_spec, r.conduit
        # terminal (roadName)
        term = _nearest(terms, ld.x, SLD_CFG["load_terminal_x_tol"] * s)
        road = term.text.upper() if term else ""
        is_spare = "SPARE" in ld.text.upper() or "DỰ PHÒNG" in ld.text.upper()
        if is_spare:
            size = spec = conduit = ""
            if not road:
                road = "SPARE"
        res.items.append({
            "panelName": res.panel_name,
            "roadName": road,
            "loadName": _clean_load(ld.text),
            "itemGroup": "Dây & cáp điện",
            "itemName": "Dây/cáp Cu/PVC",
            "size": size,
            "cableSpec": spec,
            "conduit": conduit,
        })

    res.debug = {
        "region": [round(v) for v in region],
        "n_routes": len(routes),
        "n_slashes": len(slashes),
        "n_terminals": len(terms),
        "n_loads": len(loads),
    }
    return res


def _merge_load_columns(loads, x_tol):
    """Gộp các dòng text dọc cùng cột (vd tên Việt + Anh) thành 1 tải."""
    loads = sorted(loads, key=lambda v: v.x)
    out: list[TextItem] = []
    for v in loads:
        if out and abs(out[-1].x - v.x) <= x_tol:
            out[-1].text += " " + v.text
        else:
            out.append(TextItem(v.text, v.x, v.y, vertical=True))
    return out


# các mốc tiếng Anh để cắt bỏ phần dịch lặp (giữ lại phần tiếng Việt)
_EN_MARKERS = [
    " SOCKET", " FOR ", " WATER HEATER", " INDUCTION", " EXHAUST", " LIGHTING",
    " ODU", " WASHING", " MACHINE", " FRIDGE", " KITCHEN", " COOKER", " SPARE",
]


def _clean_load(text: str) -> str:
    """Giữ phần tiếng Việt: cắt ở dấu '/' trước, rồi cắt tại mốc tiếng Anh."""
    name = text.split("/")[0]          # bỏ phần dịch sau '/'
    up = name.upper()
    cut = len(name)
    for mk in _EN_MARKERS:             # với cột Việt+Anh nối bằng space (không '/')
        i = up.find(mk)
        if i != -1:
            cut = min(cut, i)
    return name[:cut].strip(" /").strip()


def extract_sld_from_pdf(path: str, page_index: int) -> SLDResult:
    doc = fitz.open(path)
    try:
        return extract_sld(doc[page_index], page_index)
    finally:
        doc.close()
