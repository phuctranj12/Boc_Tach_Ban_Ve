"""KIỂU B — Bảng/ma trận tủ điện (panel schedule dạng cột).

Đặc trưng: thông tin xếp thành BẢNG, mỗi CỘT là một lộ/mạch, được neo bởi
SỐ MẠCH (S1, S2, FCU 1, SS1.1...) ở một hàng ngang phía dưới. Trong mỗi cột,
text dọc gồm: loại cáp ("CU/PVC 2X(1X2.5MM2)..."), ống ("ĐI TRONG ỐNG PVC D20"),
tên tải ("Ổ CẮM PHÒNG ĂN LỚN").

Phân loại theo NỘI DUNG text (không hardcode toạ độ hàng) nên linh hoạt với
nhiều cách trình bày: có mm2 & không phải ống -> cáp; có 'ỐNG' -> ống; còn lại
là tên tải.
"""
from __future__ import annotations

import re

import fitz

from .base import (
    TakeoffItem, TakeoffResult,
    collect_horizontal_lines, collect_vertical_lines,
    parse_size, is_spare,
)

# số mạch / lộ làm neo cột
_REF_RE = re.compile(r"^(?:S\d+|FCU\s*\d+|SS\d+\.\d+|P\d+|L\d+|C\d+|H\d+)$", re.IGNORECASE)
# nhãn tủ (panel) để gán panelName
_PANEL_RE = re.compile(r"^(?:TĐ[-\s]?T?M?\d|TĐTM-?\d|TĐ-?T\d|MSB|MDB|DB[-/]\S+)", re.IGNORECASE)
_TITLE_SKIP = re.compile(r"TỦ ĐIỆN|TẦNG|SMARTHOME|SƠ ĐỒ|DIỄN GIẢI|LOẠI CÁP|CÔNG SUẤT", re.IGNORECASE)

CFG = {
    "col_x_tol": 9,        # text dọc thuộc cột nếu |x - ref.x| <= tol
    "col_y_up": 160,       # quét lên trên ref bao nhiêu point (cáp/ống/tải dọc)
    "col_y_gap": 6,        # phần text phải nằm trên ref
    "col_y_up_h": 230,     # quét lên trên ref cho text NGANG (công suất, CB)
    "col_x_right_h": 14,   # CB/công suất lệch phải tối đa so với số mạch
}

_POWER_RE = re.compile(r"^\d{2,6}$")           # số công suất (W)
_CB_RE = re.compile(r"^(?:MCB|MCCB|RCBO|RCCB|ELCB|\d+P|\d+A|\d+mA|\d+kA)$", re.IGNORECASE)
# tủ tổng TĐ-Tx (có P/Ptt/Kđt) và tủ con smarthome TĐTM-x (có công suất feeder)
_MAIN_PANEL_RE = re.compile(r"^TĐ-?T\d$", re.IGNORECASE)
_SUB_PANEL_RE = re.compile(r"^TĐTM-?\d$", re.IGNORECASE)
_PNUM_RE = re.compile(r"(\d[\d.]*)")


def _is_cable(t: str) -> bool:
    up = t.upper()
    return "MM2" in up and "ỐNG" not in up


def _is_conduit(t: str) -> bool:
    return "ỐNG" in t.upper()


def detect_score(page: fitz.Page) -> float:
    """Điểm khả năng là Kiểu B: số mạch có CỘT CÁP DỌC căn thẳng ngay phía trên.

    Đây là dấu hiệu riêng của bảng/ma trận (mỗi lộ có cáp riêng trong cột),
    khác Kiểu A (cáp gom bên trái, không thẳng cột với số mạch).
    """
    h = collect_horizontal_lines(page)
    v = collect_vertical_lines(page)
    cables = [t for t in v if _is_cable(t.text)]
    refs = [t for t in h if _REF_RE.match(t.text)]
    aligned = 0
    for ref in refs:
        if any(abs(c.x - ref.x) <= CFG["col_x_tol"]
               and ref.y - CFG["col_y_up"] <= c.y <= ref.y - CFG["col_y_gap"]
               for c in cables):
            aligned += 1
    return aligned


def extract(page: fitz.Page, page_index: int) -> TakeoffResult:
    res = TakeoffResult(page=page_index, diagram_type="panel_table")
    horiz = collect_horizontal_lines(page)
    verts = collect_vertical_lines(page)

    refs = [t for t in horiz if _REF_RE.match(t.text)]
    if not refs:
        res.debug["error"] = "Không tìm thấy số mạch (S1, FCU, SS...) — không phải bảng tủ điện."
        return res

    panels = [t for t in (horiz + verts)
              if _PANEL_RE.match(t.text) and not _TITLE_SKIP.search(t.text)]

    # Gán tủ THEO CỤM cột (chính xác hơn nearest từng item): mỗi section có vài
    # cụm cột tách nhau bởi khoảng trống; cả cụm dùng chung 1 tên tủ.
    ref_panel = _assign_panels_by_cluster(refs, panels)

    for ref in refs:
        col = [v for v in verts
               if abs(v.x - ref.x) <= CFG["col_x_tol"]
               and ref.y - CFG["col_y_up"] <= v.y <= ref.y - CFG["col_y_gap"]]
        col.sort(key=lambda v: v.y)

        cable_parts = [v.text for v in col if _is_cable(v.text)]
        conduit = next((v.text for v in col if _is_conduit(v.text)), "")
        loads = [v.text for v in col
                 if not _is_cable(v.text) and not _is_conduit(v.text)
                 and not _TITLE_SKIP.search(v.text)]

        # text NGANG cùng cột phía trên ref: công suất (số) + CB (MCB/RCBO...).
        # Cột CB thường lệch PHẢI so với số mạch -> cửa sổ bất đối xứng.
        hcol = [h for h in horiz
                if ref.x - 3 <= h.x <= ref.x + CFG["col_x_right_h"]
                and ref.y - CFG["col_y_up_h"] <= h.y < ref.y]
        power = _pick_power(hcol)
        cb = _pick_cb(hcol)

        cable = _norm(" ".join(cable_parts))
        load = _norm(_pick_load(loads))
        item = TakeoffItem(
            panelName=ref_panel.get(id(ref), ""),
            roadName=_norm(ref.text.upper()),
            loadName=load,
            power=power,
            cb=cb,
            cableSpec=cable,
            conduit=_clean_conduit(conduit),
            size=parse_size(cable),
        )
        if (is_spare(load) or is_spare(cable)) and not load:
            item.loadName = "DỰ PHÒNG"
        res.items.append(item)

    res.panel_name = _dominant(res.items)
    res.panels = _collect_panels(horiz)

    # CHÍNH TỦ con (TĐTM-x) cũng là 1 cột trong ma trận (neo bởi nhãn tủ): có
    # MCB đầu nguồn, cáp cấp nguồn, ống luồn, công suất. Tủ con cần dây nên phải
    # vào BOQ -> thêm 1 dòng feeder đầu mỗi nhóm (giữ nguyên cách gom tủ).
    feeders = []
    for ref in [t for t in horiz if _SUB_PANEL_RE.match(t.text)]:
        name = _norm(ref.text).upper()
        col = [v for v in verts
               if abs(v.x - ref.x) <= CFG["col_x_tol"]
               and ref.y - CFG["col_y_up"] <= v.y <= ref.y - CFG["col_y_gap"]]
        col.sort(key=lambda v: v.y)
        cable_parts = [v.text for v in col if _is_cable(v.text)]
        conduit = next((v.text for v in col if _is_conduit(v.text)), "")
        # tên tải feeder = mô tả tủ (KHÔNG bỏ "TỦ ĐIỆN"/"TẦNG" như lộ thường)
        loads = [v.text for v in col if not _is_cable(v.text) and not _is_conduit(v.text)]

        hcol = [h for h in horiz
                if ref.x - 3 <= h.x <= ref.x + CFG["col_x_right_h"]
                and ref.y - CFG["col_y_up_h"] <= h.y < ref.y]
        cable = _norm(" ".join(cable_parts))
        feeders.append(TakeoffItem(
            panelName=name,
            roadName=name,
            loadName=_norm(" ".join(loads)),
            power=_pick_power(hcol),
            cb=_pick_cb(hcol),
            cableSpec=cable,
            conduit=_clean_conduit(conduit),
            size=parse_size(cable),
        ))
    res.items = feeders + res.items

    res.debug = {
        "n_refs": len(refs),
        "n_vertical": len(verts),
        "n_panels": len(panels),
        "clusters": sorted(set(ref_panel.values())),
    }
    return res


def _pick_power(hcol) -> str:
    """Công suất (W) = số thuần gần ref nhất (y lớn nhất)."""
    nums = [h for h in hcol if _POWER_RE.match(h.text)]
    if not nums:
        return ""
    return max(nums, key=lambda h: h.y).text


def _pick_cb(hcol) -> str:
    """Ghép token CB (MCB/RCBO + cực + dòng + mA + kA) theo thứ tự từ trên xuống."""
    toks = [h for h in hcol if _CB_RE.match(h.text)]
    toks.sort(key=lambda h: h.y)
    return _norm(" ".join(t.text for t in toks))


def _collect_panels(horiz) -> list[dict]:
    """Thông tin tủ kèm công suất:
       - Tủ tổng TĐ-Tx: P, Ptt, Kđt (text gần nhãn).
       - Tủ con smarthome TĐTM-x: công suất = số (W) thẳng cột với nhãn (dòng feeder).
    """
    out = []
    nums = [h for h in horiz if _POWER_RE.match(h.text)]

    for a in [h for h in horiz if _MAIN_PANEL_RE.match(h.text)]:
        near = [h for h in horiz if abs(h.x - a.x) <= 70 and a.y - 8 <= h.y <= a.y + 36]
        info = {"name": a.text.upper(), "kind": "main", "power": "", "ptt": "", "kdt": ""}
        for h in near:
            up = h.text.upper().replace(" ", "")
            if up.startswith("PTT:"):
                m = _PNUM_RE.search(h.text.split(":", 1)[1]); info["ptt"] = m.group(1) if m else ""
            elif up.startswith("P:"):
                m = _PNUM_RE.search(h.text.split(":", 1)[1]); info["power"] = m.group(1) if m else ""
            elif "KĐT" in up or "KDT" in up:
                m = _PNUM_RE.search(h.text.split(":", 1)[-1]); info["kdt"] = m.group(1) if m else ""
        out.append(info)

    for a in [h for h in horiz if _SUB_PANEL_RE.match(h.text)]:
        cand = [n for n in nums if abs(n.x - a.x) <= 10 and a.y - 18 <= n.y <= a.y + 4]
        power = max(cand, key=lambda n: n.y).text if cand else ""
        out.append({"name": a.text.upper(), "kind": "sub", "power": power, "ptt": "", "kdt": ""})

    return out


def _assign_panels_by_cluster(refs, panels) -> dict[int, str]:
    """Gom refs thành cụm (theo section y rồi theo khoảng trống x), mỗi cụm 1 tủ.

    - Cụm toàn số mạch sưởi (SS...) -> 'TĐ-SƯỞI'.
    - Còn lại -> nhãn tủ (TĐTM-x / TĐ-Tx) gần mép trái cụm nhất, cùng dải y.
    """
    out: dict[int, str] = {}
    by_section: dict[int, list] = {}
    for r in refs:
        by_section.setdefault(round(r.y / 40), []).append(r)

    for group in by_section.values():
        group.sort(key=lambda t: t.x)
        # tách cụm theo khoảng trống x
        clusters, cur = [], [group[0]]
        for a, b in zip(group, group[1:]):
            if b.x - a.x <= 30:
                cur.append(b)
            else:
                clusters.append(cur)
                cur = [b]
        clusters.append(cur)

        for cl in clusters:
            cl_y = sum(t.y for t in cl) / len(cl)
            cl_left = cl[0].x
            if all(t.text.upper().startswith("SS") for t in cl):
                name = "TĐ-SƯỞI"
            else:
                name = _label_for_cluster(panels, cl_left, cl_y)
            for t in cl:
                out[id(t)] = name
    return out


def _label_for_cluster(panels, cl_left, cl_y, y_tol=70) -> str:
    """Nhãn tủ gần mép trái cụm nhất, trong cùng dải y với hàng số mạch."""
    cands = [p for p in panels if abs(p.y - cl_y) <= y_tol]
    if not cands:
        cands = panels
    if not cands:
        return ""
    # ưu tiên nhãn nằm bên trái/ngay đầu cụm
    best = min(cands, key=lambda p: abs(p.x - cl_left) + (0 if p.x <= cl_left + 10 else 25))
    return _norm(best.text).upper()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _clean_conduit(s: str) -> str:
    """'ĐI TRONG ỐNG PVC D20' -> 'ỐNG PVC D20'."""
    s = _norm(s)
    return re.sub(r"^ĐI\s+TRONG\s+", "", s, flags=re.IGNORECASE)


def _pick_load(loads: list[str]) -> str:
    """Chọn cụm mô tả tải hợp lý nhất (dài nhất, ưu tiên có chữ tiếng Việt)."""
    if not loads:
        return ""
    return max(loads, key=lambda s: (len(s), s))


def _dominant(items: list[TakeoffItem]) -> str:
    from collections import Counter
    c = Counter(it.panelName for it in items if it.panelName)
    return c.most_common(1)[0][0] if c else ""
