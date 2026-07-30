"""KIỂU B — Bảng/ma trận tủ điện (panel schedule dạng cột).

Đặc trưng: thông tin xếp thành BẢNG, mỗi CỘT là một lộ/mạch, được neo bởi
SỐ MẠCH (S1, S2, FCU 1, SS1.1...) ở một hàng ngang phía dưới. Trong mỗi cột,
text dọc gồm: loại cáp ("CU/PVC 2X(1X2.5MM2)..."), ống ("ĐI TRONG ỐNG PVC D20"),
tên tải ("Ổ CẮM PHÒNG ĂN LỚN").

Phân loại theo NỘI DUNG text (không hardcode toạ độ hàng) nên linh hoạt với
nhiều cách trình bày: có mm2 & không phải ống -> cáp; có 'ỐNG' -> ống; còn lại
là tên tải.

BẤT BIẾN TỶ LỆ: khi 1 tủ được tách riêng sang khổ giấy khác (hoặc bản vẽ xuất ở
tỷ lệ plot khác), toàn bộ hình phóng to/thu nhỏ nên MỌI khoảng cách tính bằng
point đều đổi theo. Vì vậy CFG_X/CFG_Y chỉ là ngưỡng ở TỶ LỆ CHUẨN, lúc dùng
nhân với tỷ lệ đo được ngay trên trang (`_scales`) — cùng cách hotel_db
calibrate theo `text_scale`.
"""
from __future__ import annotations

import re

import fitz

from .base import (
    TakeoffItem, TakeoffResult,
    collect_horizontal_lines, collect_vertical_lines,
    parse_size, is_spare, text_scale,
)

# số mạch / lộ làm neo cột
_REF_RE = re.compile(r"^(?:S\d+|FCU\s*\d+|SS\d+\.\d+|P\d+|L\d+|C\d+|H\d+)$", re.IGNORECASE)
# nhãn tủ (panel) để gán panelName
_PANEL_RE = re.compile(r"^(?:TĐ[-\s]?T?M?\d|TĐTM-?\d|TĐ-?T\d|MSB|MDB|DB[-/]\S+)", re.IGNORECASE)
_TITLE_SKIP = re.compile(r"TỦ ĐIỆN|TẦNG|SMARTHOME|SƠ ĐỒ|DIỄN GIẢI|LOẠI CÁP|CÔNG SUẤT", re.IGNORECASE)

# Hai mốc calibrate của bản vẽ CHUẨN (types/type2.pdf). Trang ở tỷ lệ khác chỉ
# việc nhân ngưỡng lên — xem `_scales()`.
_BASE_PITCH = 16.6      # bước cột: khoảng cách x giữa 2 số mạch cạnh nhau
_BASE_TEXT_H = 3.84     # chiều cao chữ trung vị

# Ngưỡng theo phương NGANG: co giãn theo BƯỚC CỘT (đo đúng thứ chúng đang chặn).
# Không dùng chiều cao chữ ở đây — cột hẹp mà nới tay ngang là ăn nhầm cột bên.
CFG_X = {
    "col_x_tol": 9,        # text dọc thuộc cột nếu |x - ref.x| <= tol
    "col_x_right_h": 14,   # CB/công suất lệch phải tối đa so với số mạch
    "col_x_left_h": 3,     # ... và lệch trái tối đa
    "cluster_x_gap": 30,   # khoảng trống x tách 2 cụm cột (2 tủ cạnh nhau)
    "cluster_pen": 25,     # phạt nhãn tủ nằm lệch phải cụm
    "panel_near_x": 70,    # bán kính x tìm P/Ptt/Kđt quanh nhãn tủ tổng
    "pnum_x_tol": 10,      # số công suất phải thẳng cột với nhãn tủ con
}

# Ngưỡng theo phương DỌC: co giãn theo CHIỀU CAO CHỮ (chiều dài chuỗi text dọc
# tỷ lệ với cỡ chữ, không liên quan bề rộng cột).
CFG_Y = {
    "col_y_up": 200,       # quét lên trên ref bao nhiêu point (cáp/ống/tải dọc)
    "col_y_gap": 6,        # phần text phải nằm trên ref
    "col_y_up_h": 230,     # quét lên trên ref cho text NGANG (công suất, CB)
    "row_y_tol": 40,       # 2 số mạch lệch y <= tol => cùng HÀNG (cùng sơ đồ tủ)
    "panel_y_tol": 70,     # nhãn tủ phải cùng dải y với hàng số mạch
    "panel_near_up": 8,    # dải y quanh nhãn tủ tổng khi tìm P/Ptt/Kđt
    "panel_near_dn": 36,
    "pnum_up": 18,         # dải y quanh nhãn tủ con khi tìm số công suất
    "pnum_dn": 4,
}


def _pitch(refs, row_tol: float) -> float:
    """Bước cột = TRUNG VỊ khoảng cách x giữa 2 số mạch cạnh nhau trong cùng hàng.

    Dùng trung vị nên khoảng trống lớn giữa 2 cụm tủ không kéo lệch kết quả.
    """
    gaps = []
    for row in _rows_by_y(refs, row_tol):
        row.sort(key=lambda t: t.x)
        gaps += [b.x - a.x for a, b in zip(row, row[1:]) if b.x - a.x > 0.05]
    if len(gaps) < 3:
        return 0.0
    gaps.sort()
    return gaps[len(gaps) // 2]


def _scales(page: fitz.Page, refs) -> tuple[float, float]:
    """(tỷ lệ NGANG, tỷ lệ DỌC) của trang so với bản vẽ chuẩn.

    Tách riêng 1 tủ ra khổ giấy khác = phóng to/thu nhỏ toàn hình: cột vẫn là
    cột, chỉ khoảng cách tính bằng point là đổi. Đo tỷ lệ ngay trên chính bản vẽ
    nên không phụ thuộc khổ giấy hay tỷ lệ plot.
    """
    th = text_scale(page)
    sy = th / _BASE_TEXT_H if th else 0.0
    # Hàng: dung sai theo chiều cao trang -> không cần biết tỷ lệ trước.
    pitch = _pitch(refs, max(3.0, 0.01 * page.rect.height))
    sx = pitch / _BASE_PITCH if pitch else 0.0
    # Thiếu mốc nào thì mượn mốc còn lại (bản vẽ chỉ có 1–2 lộ, chữ quá nhỏ...).
    sx = sx or sy or 1.0
    sy = sy or sx or 1.0
    # Hai mốc đo cùng một phép phóng to/thu nhỏ nên phải xấp xỉ nhau. Lệch quá 2
    # lần = mốc chữ hỏng (bản vẽ thu nhỏ tới mức text_scale lọc mất chữ bảng, chỉ
    # còn chữ tiêu đề) -> tin mốc hình học.
    if not 0.5 <= sy / sx <= 2.0:
        sy = sx
    clamp = lambda v: min(8.0, max(0.25, v))
    return clamp(sx), clamp(sy)


def _cfg(sx: float, sy: float) -> dict:
    """Toàn bộ ngưỡng đã quy về tỷ lệ của trang đang đọc."""
    return {**{k: v * sx for k, v in CFG_X.items()},
            **{k: v * sy for k, v in CFG_Y.items()}}

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
    cfg = _cfg(*_scales(page, refs))
    aligned = 0
    for ref in refs:
        if any(abs(c.x - ref.x) <= cfg["col_x_tol"]
               and ref.y - cfg["col_y_up"] <= c.y <= ref.y - cfg["col_y_gap"]
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

    sx, sy = _scales(page, refs)
    cfg = _cfg(sx, sy)

    panels = [t for t in (horiz + verts)
              if _PANEL_RE.match(t.text) and not _TITLE_SKIP.search(t.text)]

    # Gán tủ THEO CỤM cột (chính xác hơn nearest từng item): mỗi section có vài
    # cụm cột tách nhau bởi khoảng trống; cả cụm dùng chung 1 tên tủ.
    ref_panel = _assign_panels_by_cluster(refs, panels, cfg)

    for ref in refs:
        col = [v for v in verts
               if abs(v.x - ref.x) <= cfg["col_x_tol"]
               and ref.y - cfg["col_y_up"] <= v.y <= ref.y - cfg["col_y_gap"]]
        col.sort(key=lambda v: v.y)

        cable_parts = [v.text for v in col if _is_cable(v.text)]
        conduit = next((v.text for v in col if _is_conduit(v.text)), "")
        loads = [v.text for v in col
                 if not _is_cable(v.text) and not _is_conduit(v.text)
                 and not _TITLE_SKIP.search(v.text)]

        # text NGANG cùng cột phía trên ref: công suất (số) + CB (MCB/RCBO...).
        # Cột CB thường lệch PHẢI so với số mạch -> cửa sổ bất đối xứng.
        hcol = [h for h in horiz
                if ref.x - cfg["col_x_left_h"] <= h.x <= ref.x + cfg["col_x_right_h"]
                and ref.y - cfg["col_y_up_h"] <= h.y < ref.y]
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
    res.panels = _collect_panels(horiz, cfg)

    # CHÍNH TỦ con (TĐTM-x) cũng là 1 cột trong ma trận (neo bởi nhãn tủ): có
    # MCB đầu nguồn, cáp cấp nguồn, ống luồn, công suất. Tủ con cần dây nên phải
    # vào BOQ -> thêm 1 dòng feeder đầu mỗi nhóm (giữ nguyên cách gom tủ).
    feeders = []
    for ref in [t for t in horiz if _SUB_PANEL_RE.match(t.text)]:
        name = _norm(ref.text).upper()
        col = [v for v in verts
               if abs(v.x - ref.x) <= cfg["col_x_tol"]
               and ref.y - cfg["col_y_up"] <= v.y <= ref.y - cfg["col_y_gap"]]
        col.sort(key=lambda v: v.y)
        cable_parts = [v.text for v in col if _is_cable(v.text)]
        conduit = next((v.text for v in col if _is_conduit(v.text)), "")
        # tên tải feeder = mô tả tủ (KHÔNG bỏ "TỦ ĐIỆN"/"TẦNG" như lộ thường)
        loads = [v.text for v in col if not _is_cable(v.text) and not _is_conduit(v.text)]

        hcol = [h for h in horiz
                if ref.x - cfg["col_x_left_h"] <= h.x <= ref.x + cfg["col_x_right_h"]
                and ref.y - cfg["col_y_up_h"] <= h.y < ref.y]
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
        # tỷ lệ đo được của trang (1.0 = như bản vẽ chuẩn) — soi khi bóc lệch
        "scale_x": round(sx, 3),
        "scale_y": round(sy, 3),
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


def _collect_panels(horiz, cfg) -> list[dict]:
    """Thông tin tủ kèm công suất:
       - Tủ tổng TĐ-Tx: P, Ptt, Kđt (text gần nhãn).
       - Tủ con smarthome TĐTM-x: công suất = số (W) thẳng cột với nhãn (dòng feeder).
    """
    out = []
    nums = [h for h in horiz if _POWER_RE.match(h.text)]

    for a in [h for h in horiz if _MAIN_PANEL_RE.match(h.text)]:
        near = [h for h in horiz
                if abs(h.x - a.x) <= cfg["panel_near_x"]
                and a.y - cfg["panel_near_up"] <= h.y <= a.y + cfg["panel_near_dn"]]
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
        cand = [n for n in nums
                if abs(n.x - a.x) <= cfg["pnum_x_tol"]
                and a.y - cfg["pnum_up"] <= n.y <= a.y + cfg["pnum_dn"]]
        power = max(cand, key=lambda n: n.y).text if cand else ""
        out.append({"name": a.text.upper(), "kind": "sub", "power": power, "ptt": "", "kdt": ""})

    return out


def _rows_by_y(refs, tol) -> list[list]:
    """Gom refs thành từng HÀNG số mạch theo KHOẢNG CÁCH y.

    Gom theo khoảng cách chứ không chia lưới cố định (`round(y/40)`): hàng nằm
    đúng mép ô lưới sẽ không bị tách đôi thành 2 'section' giả.
    """
    rows: list[list] = []
    for r in sorted(refs, key=lambda t: t.y):
        if rows and r.y - rows[-1][-1].y <= tol:
            rows[-1].append(r)
        else:
            rows.append([r])
    return rows


def _assign_panels_by_cluster(refs, panels, cfg) -> dict[int, str]:
    """Gom refs thành cụm (theo hàng y rồi theo khoảng trống x), mỗi cụm 1 tủ.

    - Cụm toàn số mạch sưởi (SS...) -> 'TĐ-SƯỞI'.
    - Còn lại -> nhãn tủ (TĐTM-x / TĐ-Tx) gần mép trái cụm nhất, cùng dải y.
    """
    out: dict[int, str] = {}
    for group in _rows_by_y(refs, cfg["row_y_tol"]):
        group.sort(key=lambda t: t.x)
        # tách cụm theo khoảng trống x
        clusters, cur = [], [group[0]]
        for a, b in zip(group, group[1:]):
            if b.x - a.x <= cfg["cluster_x_gap"]:
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
                name = _label_for_cluster(panels, cl_left, cl_y, cfg)
            for t in cl:
                out[id(t)] = name
    return out


def _label_for_cluster(panels, cl_left, cl_y, cfg) -> str:
    """Nhãn tủ gần mép trái cụm nhất, trong cùng dải y với hàng số mạch."""
    cands = [p for p in panels if abs(p.y - cl_y) <= cfg["panel_y_tol"]]
    if not cands:
        cands = panels
    if not cands:
        return ""
    # ưu tiên nhãn nằm bên trái/ngay đầu cụm (phạt nhãn nằm lệch phải)
    near, penalty = cfg["pnum_x_tol"], cfg["cluster_pen"]
    best = min(cands, key=lambda p: abs(p.x - cl_left) + (0 if p.x <= cl_left + near else penalty))
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
