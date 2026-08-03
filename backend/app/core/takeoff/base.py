"""Khung dùng chung cho bóc tách khối lượng (QS) từ các loại sơ đồ.

Mỗi loại bản vẽ (busbar+slash, panel-table, nối trực tiếp...) là một extractor
riêng nhưng cùng trả về TakeoffResult với schema item GIỐNG NHAU. Nhờ vậy API,
frontend và bước xuất BOQ không phải biết bản vẽ thuộc loại nào.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import fitz

from ..page_text import text_dict as _text_dict, text_words as _text_words

_SIZE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*mm2", re.IGNORECASE)


@dataclass
class TextItem:
    text: str
    x: float          # tâm x
    y: float          # tâm y
    vertical: bool = False


@dataclass
class TakeoffItem:
    """Một lộ/tải = một dòng bóc tách."""
    panelName: str = ""    # nhóm chính hiển thị (SLD khách sạn: KHU VỰC, vd "PUMP ROOM")
    panelCode: str = ""    # mã tủ trên bản vẽ (vd "DB-B-MH-DWP") — tham chiếu phụ
    roadName: str = ""
    loadName: str = ""
    power: str = ""        # công suất (W) của lộ, nếu bản vẽ có
    cb: str = ""           # CB đầu lộ: MCCB/RCBO... vd "RCBO 2P 20A 30mA 6kA"
    size: str = ""
    cableSpec: str = ""
    conduit: str = ""
    # Nhóm/tên vật tư: mặc định là cáp điện (extractor SLD không phải đụng tới).
    # Extractor loại khác (vd MEP thang–máng cáp) tự đặt giá trị riêng.
    itemGroup: str = "Dây & cáp điện"
    itemName: str = "Dây/cáp Cu/PVC"
    qty: int = 1           # số lần xuất hiện/callout (mặc định 1)

    def to_dict(self) -> dict:
        # Schema gọn theo yêu cầu: chỉ 8 trường (panelName/roadName/loadName +
        # itemGroup/itemName + size/cableSpec/conduit). Bỏ panelCode/power/cb/qty.
        return {
            "panelName": self.panelName,
            "roadName": self.roadName,
            "loadName": self.loadName,
            "itemGroup": self.itemGroup,
            "itemName": self.itemName,
            "size": self.size,
            "cableSpec": self.cableSpec,
            "conduit": self.conduit,
        }


@dataclass
class TakeoffResult:
    page: int
    diagram_type: str = "unknown"     # busbar_slash | panel_table | ...
    panel_name: str = ""
    items: list[TakeoffItem] = field(default_factory=list)
    panels: list[dict] = field(default_factory=list)  # tủ tổng: name/power/ptt/kdt
    debug: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "page": self.page,
            "diagramType": self.diagram_type,
            "panelName": self.panel_name,
            "panels": self.panels,
            "items": [it.to_dict() for it in self.items],
            "debug": self.debug,
        }


# ---------- tiện ích đọc PDF dùng chung ----------
# Mọi hàm dưới đây đọc text qua page_text.* để cả 4 extractor dùng chung một lượt
# parse cho mỗi trang (xem app/core/page_text.py).
# Cửa sổ chiều cao chữ "hợp lệ" ở cỡ in thường: dưới 2px là vệt/artifact, trên 40px
# là chữ tiêu đề khung tên. Cửa sổ TUYỆT ĐỐI này chỉ đúng quanh tỷ lệ 1 — xem
# `text_scale` để biết cách nhận ra lúc nó hết đúng.
_H_MIN, _H_MAX = 2.0, 40.0


def _robust_median(hs: list[float]) -> float:
    """Trung vị 2 vòng, KHÔNG dùng mốc px tuyệt đối nào: lấy trung vị thô rồi chỉ
    giữ các giá trị quanh nó (¼×…4×) và lấy trung vị lại. Nhờ không có hằng số px,
    hàm này đúng ở MỌI tỷ lệ; đổi lại nó nhạy hơn với trang trộn nhiều cỡ chữ nên
    chỉ dùng làm phương án dự phòng."""
    import statistics
    if not hs:
        return 0.0
    m0 = statistics.median(hs)
    keep = [h for h in hs if 0.25 * m0 <= h <= 4 * m0]
    return statistics.median(keep) if keep else m0


def text_scale(page: fitz.Page) -> float:
    """Chiều cao chữ TRUNG VỊ (px) — proxy TỶ LỆ plot của bản vẽ (ổn định theo tỷ
    lệ, không phụ thuộc mật độ nội dung). Dùng để tự suy các ngưỡng khoảng cách
    (extractor calibrate ở baseline rồi nhân theo tỷ lệ này).

    BẤT BIẾN TỶ LỆ: cửa sổ lọc (2..40px) là mốc TUYỆT ĐỐI nên tự nó chỉ đúng trong
    khoảng ~0.25x–4x. Ngoài dải đó nó cắt cụt phân bố và trả về tỷ lệ SAI (bản vẽ
    phóng 5x: mọi chữ >40px bị loại, chỉ còn vài chữ nhỏ sót → tưởng là bản vẽ
    thường). Nhận ra tình huống này bằng chính kết quả: trung vị nằm sát mép cửa sổ
    ⇒ cửa sổ đang cắt vào phân bố ⇒ đo lại bằng cách KHÔNG có mốc tuyệt đối.

    ĐÃ THỬ và BỎ: thêm mốc "số chữ bị loại vì quá to > số chữ lọt cửa sổ". Nó bắt
    thêm được vài ca phóng ≥6x, nhưng trên trang BỊ XOAY thì chữ dọc được PyMuPDF
    báo chiều cao span bằng ĐỘ DÀI cả dòng ⇒ mốc đó bắn nhầm và làm hỏng việc chọn
    hướng. Nếu cần nới đầu trên, hãy đo trên CHIỀU NGANG của glyph chứ đừng đếm span.
    """
    import statistics
    hs_all = []
    for b in _text_dict(page)["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                bb = s["bbox"]
                h = abs(bb[3] - bb[1])
                if h > 0:
                    hs_all.append(h)
    hs = [h for h in hs_all if _H_MIN < h < _H_MAX]
    if hs:
        m = statistics.median(hs)
        if _H_MIN * 1.2 < m < _H_MAX * 0.85:      # cửa sổ chưa chạm phân bố → tin
            return m
    return _robust_median(hs_all)


def result_quality(res: "TakeoffResult") -> int:
    """Điểm CHẤT LƯỢNG của kết quả bóc (dùng chọn hướng xoay đúng): số lộ có
    'size' — bóc SAI hướng thì cáp không gắn được → size rỗng → điểm ≈ 0."""
    return sum(1 for it in res.items if it.size)


def collect_words(page: fitz.Page) -> list[TextItem]:
    """Text ngang (horizontal words)."""
    out = []
    for w in _text_words(page):
        t = w[4].strip()
        if t:
            out.append(TextItem(t, (w[0] + w[2]) / 2, (w[1] + w[3]) / 2))
    return out


def collect_vertical_lines(page: fitz.Page) -> list[TextItem]:
    """Text dọc (rotated 90°) — gộp theo line, lấy nguyên cụm."""
    out = []
    for b in _text_dict(page)["blocks"]:
        for l in b.get("lines", []):
            d = l.get("dir", (1, 0))
            if abs(d[0]) < 0.5:
                txt = "".join(s["text"] for s in l["spans"]).strip()
                if txt:
                    bb = l["bbox"]
                    out.append(TextItem(txt, (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, True))
    return out


def collect_horizontal_lines(page: fitz.Page) -> list[TextItem]:
    """Text ngang gộp theo line (giữ nguyên cụm nhiều từ)."""
    out = []
    for b in _text_dict(page)["blocks"]:
        for l in b.get("lines", []):
            d = l.get("dir", (1, 0))
            if abs(d[0]) >= 0.5:
                txt = "".join(s["text"] for s in l["spans"]).strip()
                if txt:
                    bb = l["bbox"]
                    out.append(TextItem(txt, (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, False))
    return out


def parse_size(cable_spec: str) -> str:
    """Lấy tiết diện lõi pha (số mm2 đầu tiên), chuẩn hoá '2.5mm2'."""
    m = _SIZE_RE.search(cable_spec or "")
    if not m:
        return ""
    return f"{m.group(1).replace(',', '.')}mm2"


def is_spare(text: str) -> bool:
    up = (text or "").upper()
    return "DỰ PHÒNG" in up or "SPARE" in up
