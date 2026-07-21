"""KIỂU C — Sơ đồ nguyên lý tủ điện dự án khách sạn (hotel DB).

Đặc trưng (khác Kiểu A busbar_slash & Kiểu B panel_table):
  - Nhãn CÁP 2 dạng, đều có 'mmSQ'/'mm2':
      "2 x 2.5 mmSQ/1C Cu/PVC"        (N x S)
      "4C - 16 mmSQ Cu/XLPE/PVC"      (NC - S)
    + dòng TIẾP THEO cho lõi đất & máng/ống:
      "+ E2.5 mmSQ TRONG ỐNG/MÁNG" hoặc "+ E 16 mmSQ ON TRAY/TRUNKING".
  - CB tách thành 3 token DỌC cạnh nhau: "32A 3P" + "MCCB" + "6 kA".
  - Công suất "(4.0 kW)" / "[11.5 kW]" / "[2.7/ 4.7 kW]".
  - Mỗi trang có NHIỀU tủ xếp dạng lưới; nhãn tủ "DB-/EDB-/SSB-…-MH-…".

Logic LIÊN KẾT (hình học, tất định): mỗi nhãn CÁP = 1 lộ. Chuỗi neo:
  cáp → CB GẦN NHẤT (cùng mạch) → tủ = nhãn DB gần CB nhất.
Nhờ chuỗi này, việc gán tủ không phụ thuộc khoảng offset cố định của bản vẽ
(CB luôn nằm sát thanh cái/nhãn tủ; cáp luôn nằm sát CB của nó).

Lõi `extract_items(words, hlines, vlines)` nhận 3 nhóm TextItem (chữ ngang rời /
chữ ngang đã gộp dòng / chữ dọc) nên chạy được cả từ PDF (PyMuPDF) lẫn nguồn
khác (DXF…) miễn map được dữ liệu vào 3 nhóm này.
"""
from __future__ import annotations

import math
import re

import fitz

from .base import (
    TakeoffItem, TakeoffResult, TextItem,
    collect_words, collect_vertical_lines, collect_horizontal_lines,
    is_spare, text_scale,
)

# Chiều cao chữ (px) của bản vẽ dùng để calibrate mọi ngưỡng khoảng cách. Ở tỷ lệ
# khác, ngưỡng nhân theo `text_scale(page)/_BASE_TEXT_H` (xem `extract`). ⇒ bất biến tỷ lệ.
_BASE_TEXT_H = 9.7

# ---- ngữ pháp Kiểu C ----
# Cáp: "N x S mmSQ" HOẶC "NC - S mmSQ". Loại trừ Kiểu A ("2x1C") & Kiểu B ("…X(1X…)").
_CABLE_RE = re.compile(
    r"(?:(\d+)\s*[xX]\s*([\d.]+)|(\d+)\s*C\s*-\s*([\d.]+))\s*(?:mm2|mmsq)", re.I)
_EARTH_RE = re.compile(r"\+?\s*E\s*([\d.]+)\s*(?:mm2|mmsq)", re.I)
_EARTH_LINE_RE = re.compile(r"^\+?\s*E\s*[\d.]+\s*(?:mm2|mmsq)", re.I)  # dòng nối tiếp
_FIRE_RE = re.compile(r"mica|lshf|xlpe|fire\s*rated|chống\s*cháy|chong\s*chay", re.I)
# CB tách token: rating "32A 3P" / "10A" ; loại ; cắt "6 kA"
_CB_RATING_RE = re.compile(r"^\(?\s*(\d+)\s*A(?:\s*(\d|SP|DP|TP|[SDT])\s*P?)?\s*\)?$", re.I)
_POLES_MAP = {"S": "1", "D": "2", "T": "3", "SP": "1", "DP": "2", "TP": "3"}
_CB_TYPE_RE = re.compile(r"^(MCCB|MCB|RCBO|RCCB|ELCB|ACB|MPCB)$", re.I)
_CB_BRK_RE = re.compile(r"^([\d.]+)\s*kA$", re.I)
_POWER_RE = re.compile(r"[\[(]\s*([\d.]+(?:\s*/\s*[\d.]+)?|\*\*)\s*kW\s*[\])]", re.I)
# roadName tách 3 loại nhãn: PHA (L1/L2/L3), CỤM at-tô-mát (S1/S2/P1/P3…), SỐ mạch
# động cơ (1..13). KHÔNG dùng 'C#' (C1/C2 là nhãn phụ cạnh busbar, không phải số lộ).
_PHASE_RE = re.compile(r"^L[123]$", re.I)
_GROUP_RE = re.compile(r"^[SP]\d{1,2}$", re.I)
_NUM_RE = re.compile(r"^\d{1,2}$")
_TERM_RE = re.compile(r"^(?:L[123]|[SP]\d{1,2}|\d{1,2})$", re.I)   # gộp (cho anchor)
# Thanh cái VẬT LÝ (mỗi sơ đồ đúng 1) → MỎ NEO TỦ. KHÔNG gồm 'BUSDUCT' (đó là
# NGUỒN 'FROM …/BUSDUCT', không phải thanh cái của tủ).
_BUSBAR_PHYS_RE = re.compile(r"B/Bs|BUSBAR|BUS\s*BAR|TINNED", re.I)
# Nhãn KHU VỰC/tầng cạnh mỗi sơ đồ (vd "@ PUMP ROOM", "PUBLIC AREA @ LEVEL 1",
# "KHU SPA @TẦNG 3 / SPA AREA @LEVEL 3"). Đây là KHOÁ CHIA NHÓM ưu tiên cho SLD
# khách sạn (thay cho mã tủ). Nhận diện = có từ khoá khu vực + mốc tầng/@.
# Từ khoá KHU VỰC "mạnh" (tên phòng/khu). KHÔNG gồm LIFT/SHAFT (đó là vị trí tải).
_AREA_KW_RE = re.compile(
    r"ROOM|AREA|OFFICE|LOBBY|POOL|KITCHEN|LAUNDRY|SPA\b|GYM|RISER|PUMP|PIT|MEETING"
    r"|BASEMENT|CORRIDOR|RESTAURANT|BALLROOM|CAR\s*PARK|SERVICE"
    r"|SẢNH|BỂ|BƠI|HẦM|BẾP|HỘI\s*NGHỊ|CÔNG\s*CỘNG|GIẶT|ĐỖ\s*XE", re.I)
# Mốc "đây là nhãn KHU VỰC" (không phải câu bất kỳ chứa ROOM): có @ hoặc tầng.
_AREA_MARK_RE = re.compile(r"@|LEVEL|TẦNG|FLOOR", re.I)
# Câu mô tả TẢI (không phải khu vực) — loại trừ.
_AREA_NOT_RE = re.compile(
    r"LIGHTING|OUTLET|S\.S\.O|SOCKET|Ổ\s*CẮM|CHIẾU\s*SÁNG|SPARE|DỰ\s*PHÒNG"
    r"|SHUTTER|MOTOR|\bFAN\b|COIL|CONTROL|STATUS|COMMAND|ALARM|MICA|mmSQ|mm2", re.I)
# Nhãn dạng tủ: …-MH-… (DB-/EDB-/SSB-/MCC-/LCP-…). Cùng dạng cũng dùng cho TẢI
# hạ nguồn (feeder) — phân biệt TỦ thật bằng việc có THANH CÁI/NGUỒN cạnh bên.
_DB_RE = re.compile(r"^[A-Z][A-Z0-9]{0,4}-[A-Z0-9]+-MH-[A-Z0-9]+$")
# Mỏ neo "đây là một sơ đồ tủ": thanh cái (busbar) hoặc nhãn nguồn cấp vào.
_BUSBAR_RE = re.compile(r"B/Bs|BUSBAR|TINNED|@.{0,14}LEVEL|LEVEL\)|^FROM\b|^'[A-Z]", re.I)
_SOURCE_RE = re.compile(r"^'(.+)'$")          # "FROM 'X'" → nguồn cấp X
_TITLE_ANCHOR_D = 130.0     # tủ thật: nhãn cách thanh cái/nguồn ≤ ngưỡng này
_CONT_RE = re.compile(r"(TRAY|TRUNK\w*|MÁNG|MANG|ỐNG|ONG|CONDUIT)", re.I)
# Chữ KHÔNG phải tên tải (ghi chú kỹ thuật, trạng thái BMS, thông số ngắn mạch…).
_NOISE_RE = re.compile(
    r"MAX\s*DEMAND|Ik\d|Ief|SUMMER|WINTER|STATUS|COMMAND|ALARM|SELECTION\s*SWITCH"
    r"|NEUTRAL|^NOTE|B/Bs|TINNED|BUSBAR|LEVEL|^FROM\b|kA$|^E$|^CPC$|^\(\s*\)$"
    r"|GHI\s*CH|UPDATE|HOLD", re.I)
# Mảnh vụn của chính nhãn cáp (vật liệu/đơn vị/máng) — KHÔNG được coi là tên tải.
_CABLEWORD_RE = re.compile(
    r"mm2|mmsq|Cu/|/PVC|XLPE|LSHF|MICA|\bCABLE\b|TRAY|TRUNK|CONDUIT|MÁNG|MANG"
    r"|ỐNG|\bONG\b|^\+?\s*E\d", re.I)
_WORD_RE = re.compile(r"[A-Za-zÀ-ỹ]")


def is_cable_c(t: str) -> bool:
    """Cáp Kiểu C? Loại trừ Kiểu A ('2x1C…') và Kiểu B ('…2X(1X…)')."""
    up = (t or "").upper()
    if "2X1C" in up.replace(" ", "") or "X(" in up:
        return False
    if _EARTH_LINE_RE.match(t or ""):       # dòng '+E…' là phần tiếp, không tự là cáp
        return False
    return bool(_CABLE_RE.search(t or ""))


# ---- parser từng trường ----
def parse_cable(spec: str) -> dict:
    m = _CABLE_RE.search(spec or "")
    if not m:
        return {}
    cores = m.group(1) or m.group(3)
    size = m.group(2) or m.group(4)
    e = _EARTH_RE.search(spec)
    return {
        "cores": cores,
        "size": f"{size}mm2",
        "earth": f"{e.group(1)}mm2" if e else "",
        "fire_rated": bool(_FIRE_RE.search(spec)),
        "containment": _norm_containment(spec),
    }


def _norm_containment(spec: str) -> str:
    up = (spec or "").upper()
    tray = bool(re.search(r"TRAY|TRUNK|MÁNG|MANG", up))
    cond = bool(re.search(r"ỐNG|ONG|CONDUIT", up))
    if tray and cond:
        return "Máng/Ống (tray-trunking/conduit)"
    if tray:
        return "Máng/khay cáp (tray/trunking)"
    if cond:
        return "Ống luồn (conduit)"
    return ""


def _fmt_cb(rating: str, poles: str, typ: str, brk: str) -> str:
    parts = []
    if typ:
        parts.append(typ.upper())
    if poles:
        parts.append(f"{poles}P")
    if rating:
        parts.append(f"{rating}A")
    if brk:
        parts.append(re.sub(r"\s+", "", brk) if "ka" in (brk or "").lower()
                     else f"{brk}kA")
    return " ".join(parts)


def parse_power(text: str) -> str:
    m = _POWER_RE.search(text or "")
    if not m:
        return ""
    val = re.sub(r"\s*/\s*", "/", m.group(1))
    return "" if val == "**" else f"{val} kW"


# ---- tiện ích hình học ----
def _dist(a: TextItem, b: TextItem) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _nearest(src: TextItem, pool: list[TextItem], max_d: float = math.inf):
    best, bd = None, max_d
    for it in pool:
        d = _dist(src, it)
        if d < bd:
            best, bd = it, d
    return best


# Lộ và nhãn PHA của nó căn thẳng hàng: khoảng cách y chỉ ~0-19px (đo trên type3).
# Ngoài dải này gần như chắc chắn là bám nhầm.
_PHASE_ALIGN_TOL = 22.0


def _match_one_to_one(loads: list[TextItem], phases: list[TextItem],
                      tol: float) -> dict[int, TextItem]:
    """Gán mỗi lộ ĐÚNG một nhãn pha, mỗi pha chỉ thuộc MỘT lộ (1 pole = 1 mạch).

    Vì sao KHÔNG dùng 'mỗi lộ giành pha gần nhất': khi một lộ không có pha thẳng
    hàng (pole không ghi nhãn, hoặc trang không phải SLD tủ), nó sẽ bám vào pha
    gần nhất còn lại — thường là L3 cuối cụm — khiến nhiều lộ dồn nhầm về cùng
    'L3 - S…', đè lên lộ SPARE thật. Ghép 1-1 theo khoảng cách tăng dần, chỉ nhận
    cặp thẳng hàng (≤ tol), nên lộ orphan để TRỐNG pha thay vì cướp pha của lộ khác.
    """
    pairs = []
    for i, l in enumerate(loads):
        for j, p in enumerate(phases):
            if abs(l.y - p.y) <= tol and abs(l.x - p.x) <= 450:
                pairs.append((_dist(l, p), i, j))
    pairs.sort()
    used_l: set[int] = set()
    used_p: set[int] = set()
    out: dict[int, TextItem] = {}
    for _, i, j in pairs:
        if i in used_l or j in used_p:
            continue
        used_l.add(i)
        used_p.add(j)
        out[i] = phases[j]
    return out


def _is_loadish(t: TextItem) -> bool:
    """Token mô tả TÊN TẢI? (không phải cáp/earth/CB/power/tiêu đề/ghi chú)."""
    s = t.text
    if (is_cable_c(s) or _EARTH_LINE_RE.match(s) or _POWER_RE.search(s)
            or _CB_RATING_RE.match(s) or _CB_TYPE_RE.match(s) or _CB_BRK_RE.match(s)
            or _DB_RE.match(s) or _NOISE_RE.search(s) or _CABLEWORD_RE.search(s)):
        return False
    return bool(_WORD_RE.search(s)) and len(s) >= 3


def _is_load_line(s: str) -> bool:
    """Một DÒNG TẢI (đích của 1 nhánh mạch) = 1 lộ. Loại cáp/earth/CB/tủ/khu vực/
    ghi chú; loại luôn dòng CHỈ có công suất '[..kW]' (đó là nhãn power, không phải
    tải). Giữ 'SPARE' và tải có kèm kW ('(1.2 kW) FOR FCU…')."""
    if (is_cable_c(s) or _EARTH_LINE_RE.match(s) or _DB_RE.match(s) or _is_area(s)
            or _NOISE_RE.search(s) or _CABLEWORD_RE.search(s)
            or _CB_RATING_RE.match(s) or _CB_TYPE_RE.match(s) or _CB_BRK_RE.match(s)):
        return False
    stripped = _POWER_RE.sub("", s).strip(" ()[]")
    return bool(_WORD_RE.search(stripped)) and len(stripped) >= 3


def _assign_above(anchor: TextItem, panels: list) -> object:
    """Gán lộ về THANH CÁI HEADING nó: cùng cột x, và busbar nằm PHÍA TRÊN (busbar
    ở đầu mỗi sơ đồ; sơ đồ có thể rất cao). Neo bằng nhãn PHA/CB (nằm sát busbar)
    để tránh lệch. Phạt busbar nằm dưới anchor (không thể là busbar của nó)."""
    best, bs = None, math.inf
    for b in panels:
        dy = anchor.y - b.y                     # >0: busbar ở TRÊN (đúng)
        pen = dy if dy >= 0 else -dy * 5        # busbar dưới anchor → phạt nặng
        score = abs(anchor.x - b.x) * 2 + pen
        if score < bs:
            best, bs = b, score
    return best


def _cable_above(load: TextItem, cables: list[TextItem], s: float = 1.0) -> TextItem | None:
    """Cáp của nhánh = chữ cáp GẦN NHẤT PHÍA TRÊN, cùng cột (viết 1 lần/cụm dùng
    chung). Chặn khoảng cách ≤320px (×tỷ lệ) để nhánh không có cáp riêng (vd FCU)
    khỏi mượn cáp của cụm khác."""
    best, bd = None, 320.0 * s
    for c in cables:
        if abs(c.x - load.x) <= 130 * s and -20 * s <= (load.y - c.y) <= bd:
            gap = load.y - c.y
            if gap < bd:
                best, bd = c, gap
    return best


def _load_name(cab: TextItem, loads: list[TextItem]) -> str:
    if is_spare(cab.text):
        return "DỰ PHÒNG"
    near = _nearest(cab, loads, 190)
    if near is None:
        return ""
    txt = re.sub(r"^\([^)]{0,3}\)\s*", "", near.text)  # chỉ bỏ '( )' / '(LL)' đầu
    txt = re.sub(r"\s+", " ", txt).strip(" -/")
    return "DỰ PHÒNG" if is_spare(near.text) else txt


def _panel_titles(tokens: list[TextItem]) -> list[TextItem]:
    """Lọc ra TIÊU ĐỀ tủ thật trong các nhãn dạng '…-MH-…'.

    Tổng quát (không phụ thuộc trang): một nhãn là tủ ⇔ cạnh nó (≤_TITLE_ANCHOR_D)
    có MỎ NEO sơ đồ = thanh cái ('… B/Bs', 'TINNED', '@ … LEVEL') hoặc nhãn nguồn
    ("FROM '…'"). Nhãn '…-MH-…' KHÔNG có mỏ neo là TẢI hạ nguồn (feeder) → bỏ.
    """
    cands = [t for t in tokens if _DB_RE.match(t.text)]
    anchors = [t for t in tokens if _BUSBAR_RE.search(t.text)]
    titles, seen = [], set()
    for c in cands:
        key = (round(c.x), round(c.y), c.text)
        if key in seen:
            continue
        seen.add(key)
        near = _nearest(c, anchors, _TITLE_ANCHOR_D)
        if near is not None:
            titles.append(c)
    return titles


def _dedup_pos(items: list[TextItem], r: float = 90.0) -> list[TextItem]:
    """Gộp token cùng vị trí (~r px) thành 1 — nhãn thanh cái hay tách nhiều mảnh
    ('HDHC' / 'TINNED' / 'CU.' / 'B/Bs')."""
    out: list[TextItem] = []
    for t in items:
        if all(math.hypot(t.x - o.x, t.y - o.y) > r for o in out):
            out.append(t)
    return out


def _cluster_idx(pts: list[TextItem], d: float = 280.0) -> list[list[int]]:
    """Gom các điểm thành cụm liên thông (2 điểm ≤ d px là cùng cụm) — union-find.
    Dùng cho sơ đồ KHÔNG có thanh cái: mỗi sơ đồ = 1 cụm cáp tách biệt về không gian.
    """
    n = len(pts)
    par = list(range(n))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if _dist(pts[i], pts[j]) <= d:
                par[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


class _Panel:
    """Một tủ/sơ đồ: vị trí + KHU VỰC (nhóm chính) + mã tủ (tham chiếu phụ)."""
    __slots__ = ("x", "y", "area", "code")

    def __init__(self, x: float, y: float, area: str, code: str):
        self.x, self.y, self.area, self.code = x, y, area, code


def _is_area(s: str) -> bool:
    return (bool(_AREA_KW_RE.search(s)) and bool(_AREA_MARK_RE.search(s))
            and not _AREA_NOT_RE.search(s))


def _area_at(pt: TextItem, areas: list[TextItem], max_d: float, s: float = 1.0) -> str:
    """Nhãn khu vực gần vị trí nhất; gộp các mảnh song ngữ cùng chỗ (≤55px ×tỷ lệ)."""
    a = _nearest(pt, areas, max_d)
    if not a:
        return ""
    parts = sorted((t for t in areas if _dist(a, t) < 55 * s), key=lambda t: (t.y, t.x))
    txt = re.sub(r"[()]", " ", " ".join(t.text for t in parts))
    # bỏ từ lặp liên tiếp (mảnh song ngữ hay dính '@PUMP' thừa)
    words = re.sub(r"\s+", " ", txt).strip(" -/").split(" ")
    out = [w for i, w in enumerate(words) if i == 0 or w.lower() != words[i - 1].lower()]
    return " ".join(out)


def _name_at(pt: TextItem, titles, sources, s: float = 1.0) -> str:
    """Mã tủ tại 1 vị trí: nhãn '-MH-' gần nhất, thiếu thì NGUỒN 'FROM …'."""
    t = _nearest(pt, titles, 600 * s)
    if t:
        return t.text
    src = _nearest(pt, sources, 900 * s)
    return _SOURCE_RE.match(src.text).group(1) if src else ""


def _panels(tokens: list[TextItem], cb_items: list[TextItem],
            s: float = 1.0) -> list[_Panel]:
    """Danh sách TỦ neo theo THANH CÁI (mỗi sơ đồ đúng 1 busbar) — tin cậy vì CÓ tủ
    KHÔNG ghi nhãn '-MH-' (vd sub-main/SSB). Lọc busbar THẬT: ≥2 CB bám gần (≤360px).
    Mỗi tủ mang KHU VỰC (nhóm chính, ≤300px) + mã tủ (tham chiếu). Trang KHÔNG có
    busbar hợp lệ → trả [] (bên gọi chuyển sang gom-cụm, xem `extract_items`).
    (Mọi ngưỡng ×tỷ lệ `s`.)"""
    busbars = _dedup_pos([t for t in tokens if _BUSBAR_PHYS_RE.search(t.text)], 90 * s)
    real = [b for b in busbars
            if sum(1 for c in cb_items if _dist(b, c) <= 360 * s) >= 2]
    if not real:
        return []
    titles = [t for t in tokens if _DB_RE.match(t.text)]
    sources = [t for t in tokens if _SOURCE_RE.match(t.text)]
    areas = [t for t in tokens if _is_area(t.text)]
    out = []
    for b in real:
        code = _nearest(b, titles, 280 * s)
        code = code.text if code else ""
        if not code:
            src = _nearest(b, sources, 700 * s)
            code = _SOURCE_RE.match(src.text).group(1) if src else ""
        area = _area_at(b, areas, 300 * s, s) or code   # thiếu khu vực → dùng tạm mã
        out.append(_Panel(b.x, b.y, area, code))
    return out


# ---- gom CB từ 3 token rời ----
def _build_cbs(verts: list[TextItem], s: float = 1.0) -> list[dict]:
    """Mỗi rating ('32A 3P') hút loại + 'kA' lân cận (≤45px ×tỷ lệ) → 1 CB tại rating."""
    ratings = [t for t in verts if _CB_RATING_RE.match(t.text)]
    types = [t for t in verts if _CB_TYPE_RE.match(t.text)]
    brks = [t for t in verts if _CB_BRK_RE.match(t.text)]
    cbs = []
    for r in ratings:
        m = _CB_RATING_RE.match(r.text)
        rating, poles = m.group(1), (m.group(2) or "").upper()
        poles = _POLES_MAP.get(poles, poles)
        typ = _nearest(r, types, 45 * s)
        brk = _nearest(r, brks, 45 * s)
        cbs.append({
            "x": r.x, "y": r.y,
            "text": _fmt_cb(rating, poles,
                            typ.text if typ else "",
                            brk.text if brk else ""),
        })
    return cbs


# ---- lõi tách rời nguồn ----
def extract_items(words: list[TextItem], hlines: list[TextItem],
                  vlines: list[TextItem], s: float = 1.0) -> list[TakeoffItem]:
    """words = chữ NGANG rời (cho nhãn tủ); hlines = chữ NGANG đã gộp theo dòng
    (cho cáp/earth/power/tải — là CÂU hoàn chỉnh); vlines = chữ DỌC (CB/số mạch).
    `s` = tỷ lệ bản vẽ (chiều-cao-chữ / baseline) → mọi ngưỡng khoảng cách ×s."""
    cables = [t for t in hlines if is_cable_c(t.text)]
    earths = [t for t in hlines if _EARTH_LINE_RE.match(t.text)]
    powers = [t for t in hlines if _POWER_RE.search(t.text)]
    phases = [t for t in vlines if _PHASE_RE.match(t.text)]    # L1/L2/L3
    groups = [t for t in vlines if _GROUP_RE.match(t.text)]    # S1/S2/P1… (cụm CB)
    nums = [t for t in vlines if _NUM_RE.match(t.text)]        # số mạch động cơ
    # NEO theo DÒNG TẢI: mỗi nhánh (đích tải) = 1 lộ = 1 sợi cáp.
    load_lines = [t for t in hlines if _is_load_line(t.text)]
    # + lộ ĐỘNG CƠ mà tên (tag) bị chữ XÁM (không có token): nhận qua POWER đứng
    #   một mình '(x kW)' KHÔNG kèm chữ tải VÀ không sát dòng tải nào (≠ FCU đã có tên).
    motors = [
        p for p in powers
        if not _clean_load(p.text)
        and not any(abs(l.y - p.y) <= 48 * s and abs(l.x - p.x) <= 200 * s
                    for l in load_lines)
    ]
    # mỗi phần tử = (token, is_spare, is_motor)
    anchors = ([(t, is_spare(t.text), False) for t in load_lines]
               + [(t, False, True) for t in motors])
    cbs = _build_cbs(vlines, s)
    cb_items = [TextItem(c["text"], c["x"], c["y"], True) for c in cbs]
    all_tokens = words + vlines + hlines
    areas_all = [t for t in all_tokens if _is_area(t.text)]

    # GÁN TỦ theo LOẠI layout: có busbar → về busbar gần nhất; KHÔNG busbar (thang
    # máy…) → gom DÒNG TẢI thành cụm không gian, mỗi cụm 1 tủ.
    panels = _panels(all_tokens, cb_items, s)
    load_panel: dict[int, _Panel] = {}
    if not panels:
        titles = [t for t in all_tokens if _DB_RE.match(t.text)]
        sources = [t for t in all_tokens if _SOURCE_RE.match(t.text)]
        pts = [a[0] for a in anchors]
        for grp in _cluster_idx(pts, 280 * s):
            cx = sum(pts[i].x for i in grp) / len(grp)
            cy = sum(pts[i].y for i in grp) / len(grp)
            c = TextItem("", cx, cy, False)
            code = _name_at(c, titles, sources, s)
            area = _area_at(c, areas_all, 700 * s, s) or code
            pan = _Panel(cx, cy, area, code)
            for i in grp:
                load_panel[i] = pan

    # GÁN PHA 1-1: mỗi pole (L1/L2/L3) chỉ thuộc một mạch. Chỉ ghép lộ THƯỜNG (không
    # phải motor — motor neo theo số mạch, không theo pha). Lộ không có pha thẳng hàng
    # sẽ để TRỐNG pha thay vì cướp pha xa (xem _match_one_to_one).
    load_tokens = [a[0] for a in anchors]
    non_motor_idx = [i for i, a in enumerate(anchors) if not a[2]]
    phase_of_sub = _match_one_to_one([load_tokens[i] for i in non_motor_idx],
                                     phases, _PHASE_ALIGN_TOL * s)
    phase_of = {non_motor_idx[k]: v for k, v in phase_of_sub.items()}

    rows: list[tuple] = []       # (sort_key, TakeoffItem) — sắp lại để cùng cụm liền nhau
    seen_panels: list[str] = []  # thứ tự panel xuất hiện (giữ nguyên trên bảng)
    for idx, (load, sp, is_motor) in enumerate(anchors):
        # roadName = PHA + CỤM (vd "L1 - S1") để phân biệt các nhánh trùng pha.
        # PHA: pole L# ĐÃ GHÉP 1-1 với lộ. CỤM: nhãn S#/P# gần chính NHÃN PHA (pha &
        # cụm cùng ở MCB nên sát nhau) → ghép đúng cặp, tránh lấy nhầm cụm trên.
        ph = phase_of.get(idx)
        gr = _nearest(ph, groups, 450 * s) if ph else _nearest(load, groups, 450 * s)
        if is_motor:
            n = _nearest(load, nums, 450 * s)
            road = (n.text if n else (gr.text.upper() if gr else ""))
        elif ph and gr:
            road = f"{ph.text.upper()} - {gr.text.upper()}"
        elif ph:
            road = ph.text.upper()
        else:
            road = gr.text.upper() if gr else ""
        term = ph or gr        # neo gán-tủ (nhãn sát busbar)

        # cáp = thừa hưởng chữ cáp gần nhất phía trên (bỏ qua nếu SPARE — chưa kéo).
        spec, size, cond = "", "", ""
        if not sp:
            cab = _cable_above(load, cables, s)
            if cab:
                spec = cab.text
                e = _nearest_below(cab, earths, s)
                if e:
                    spec = f"{spec} {e.text}"
                info = parse_cable(spec)
                size, cond = info.get("size", ""), info.get("containment", "")
                spec = re.sub(r"\s+", " ", spec).strip()

        cb = _nearest(load, cb_items, 500 * s)
        # neo gán-tủ = nhãn PHA/CB (sát busbar) để "busbar phía trên" chuẩn hơn.
        anchor = term or cb or load
        pan = _assign_above(anchor, panels) if panels else load_panel.get(idx)

        # công suất CHỈ lấy từ chính token của lộ (motor = token power; tải như FCU
        # ghi '(1.2 kW)' trong tên). KHÔNG mượn power lân cận → tránh gán nhầm cho
        # ổ cắm/spare cạnh động cơ.
        pw = parse_power(load.text)

        if sp:
            load_name = "DỰ PHÒNG"
        elif is_motor:
            load_name = "ĐỘNG CƠ / MOTOR"    # tag tên bị chữ xám, nhận qua công suất
        else:
            load_name = _clean_load(load.text)

        area = pan.area if pan else ""
        if area not in seen_panels:
            seen_panels.append(area)
        # KHOÁ SẮP XẾP: giữ thứ tự panel xuất hiện, trong panel gom theo CỤM (theo y
        # nhãn cụm, trên→dưới) rồi PHA (L1→L2→L3) → 3 lộ cùng S1 nằm liền nhau.
        prank = {"L1": 1, "L2": 2, "L3": 3}.get(ph.text.upper() if ph else "", 9)
        group_y = gr.y if gr else load.y
        sort_key = (seen_panels.index(area), round(group_y), prank, round(load.y))

        rows.append((sort_key, TakeoffItem(
            panelName=area,
            panelCode=(pan.code if pan else "").upper(),
            roadName=road,
            loadName=load_name,
            power=pw,
            cb="" if sp else (cb.text if cb else ""),
            size=size,
            cableSpec=spec,
            conduit=cond,
        )))
    rows.sort(key=lambda r: r[0])
    return [it for _, it in rows]


def _clean_load(text: str) -> str:
    """Bỏ tiền tố checkbox '( )'/'(LL)' và công suất '(x kW)' đầu dòng tải."""
    s = re.sub(r"^\([^)]{0,3}\)\s*", "", text)      # '( )', '(LL)'
    s = re.sub(r"^\(\s*[\d.]+\s*kW\s*\)\s*", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip(" -/")


def _nearest_below(cab: TextItem, earths: list[TextItem], s: float = 1.0):
    best, bd = None, 30.0 * s      # earth nằm sát dưới (~16px ×tỷ lệ), cùng cột
    for e in earths:
        if abs(e.x - cab.x) <= 160 * s and 0 < (e.y - cab.y) <= bd:
            d = e.y - cab.y
            if d < bd:
                best, bd = e, d
    return best


# ---- giao diện registry ----
def detect_score(page: fitz.Page) -> float:
    toks = collect_horizontal_lines(page) + collect_vertical_lines(page)
    return float(sum(1 for t in toks if is_cable_c(t.text)))


def extract(page: fitz.Page, page_index: int) -> TakeoffResult:
    words = collect_words(page)
    hlines = collect_horizontal_lines(page)
    vlines = collect_vertical_lines(page)
    # TỶ LỆ bản vẽ: chiều-cao-chữ / baseline (9.7px). File hiện tại → s=1 (không đổi
    # kết quả); bản vẽ cỡ/tỷ lệ khác → mọi ngưỡng khoảng cách tự co giãn theo s.
    th = text_scale(page)
    s = min(4.0, max(0.5, th / _BASE_TEXT_H)) if th else 1.0
    res = TakeoffResult(page=page_index, diagram_type="hotel_db")
    res.items = extract_items(words, hlines, vlines, s)
    from collections import Counter
    c = Counter(it.panelName for it in res.items if it.panelName)
    res.panel_name = c.most_common(1)[0][0] if c else ""
    res.debug = {
        "n_cables": len(res.items),
        "n_panels": len(c),
        "panels": dict(c),
        "text_scale": round(th, 2),
        "scale_factor": round(s, 3),
    }
    return res
