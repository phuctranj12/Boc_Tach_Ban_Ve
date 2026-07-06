"""Khung dùng chung cho bóc tách khối lượng (QS) từ các loại sơ đồ.

Mỗi loại bản vẽ (busbar+slash, panel-table, nối trực tiếp...) là một extractor
riêng nhưng cùng trả về TakeoffResult với schema item GIỐNG NHAU. Nhờ vậy API,
frontend và bước xuất BOQ không phải biết bản vẽ thuộc loại nào.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import fitz

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
def text_scale(page: fitz.Page) -> float:
    """Chiều cao chữ TRUNG VỊ (px) — proxy TỶ LỆ plot của bản vẽ (ổn định theo tỷ
    lệ, không phụ thuộc mật độ nội dung). Dùng để tự suy các ngưỡng khoảng cách
    (extractor calibrate ở baseline rồi nhân theo tỷ lệ này)."""
    import statistics
    hs = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                bb = s["bbox"]
                h = abs(bb[3] - bb[1])
                if 2 < h < 40:
                    hs.append(h)
    return statistics.median(hs) if hs else 0.0


def result_quality(res: "TakeoffResult") -> int:
    """Điểm CHẤT LƯỢNG của kết quả bóc (dùng chọn hướng xoay đúng): số lộ có
    'size' — bóc SAI hướng thì cáp không gắn được → size rỗng → điểm ≈ 0."""
    return sum(1 for it in res.items if it.size)


def collect_words(page: fitz.Page) -> list[TextItem]:
    """Text ngang (horizontal words)."""
    out = []
    for w in page.get_text("words"):
        t = w[4].strip()
        if t:
            out.append(TextItem(t, (w[0] + w[2]) / 2, (w[1] + w[3]) / 2))
    return out


def collect_vertical_lines(page: fitz.Page) -> list[TextItem]:
    """Text dọc (rotated 90°) — gộp theo line, lấy nguyên cụm."""
    out = []
    for b in page.get_text("dict")["blocks"]:
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
    for b in page.get_text("dict")["blocks"]:
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
