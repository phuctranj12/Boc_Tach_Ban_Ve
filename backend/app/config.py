"""Cấu hình tập trung cho toàn bộ pipeline.

Mọi ngưỡng (threshold) heuristic đều đặt ở đây để dễ tinh chỉnh độ chính xác
mà không phải đụng vào logic.
"""
from __future__ import annotations

import sys
from pathlib import Path

# --- Thư mục ---
# Khi đóng gói (PyInstaller, sys.frozen): mã nguồn nằm trong thư mục tạm chỉ-đọc,
# nên data phải ghi CẠNH file thực thi (.exe) để giữ được & người dùng thấy được.
if getattr(sys, "frozen", False):
    APP_HOME = Path(sys.executable).resolve().parent
else:
    APP_HOME = Path(__file__).resolve().parent.parent  # = backend/

BASE_DIR = APP_HOME
DATA_DIR = APP_HOME / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULT_DIR = DATA_DIR / "results"

for _d in (DATA_DIR, UPLOAD_DIR, RESULT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Phase 4: phân loại layer ---
# Tên layer CAD (phần sau dấu $0$ hoặc | trong tên xobject) được map về nhóm chức năng.
# So khớp theo substring, không phân biệt hoa thường.
LAYER_GROUPS: dict[str, list[str]] = {
    "wire": ["E-LINE", "WIRING", "CABLE", "E-PO WIRING", "E-CIRCUIT", "BUSBAR", "BUS BAR"],
    "light": ["E-LT", "E-LIGHT", "A-LIGHT", "E-LTG", "LIGHTNING"],
    "switch": ["E-SW", "2WAY", "SWITCH"],
    "socket": ["E-PO", "E_GPO", "E-GPO", "E-POWER", "SOCKET", "GPO"],
    "equipment": ["E-ELEC-EQPM", "E-EQUIP", "E-EQP", "E-MV", "MEP-E"],
    "text": ["E-TXT", "E-TEXT", "TEXT", "MEP-E-TXT"],
}

# --- Phase 3: nhận diện đối tượng qua nhãn text (regex) ---
# Thứ tự ưu tiên: nhãn nào match trước thì lấy loại đó.
LABEL_PATTERNS: list[tuple[str, str]] = [
    ("distribution_board", r"^(DB|MDB|SDB)[-/].+"),
    ("breaker", r"^\d+P-\d+A$"),                 # 1P-10A, 2P-63A
    ("breaker", r"^MCB$"),
    ("switch", r"^S\d+[A-Za-z]?$"),              # S1, S2, S1a
    ("light", r"^L\d+[A-Za-z]?$"),               # L1, L2
    ("socket", r"^P\d+[A-Za-z]?$"),              # P1, P3, P5
]

# --- Phase 5: graph builder ---
# Đơn vị toạ độ là point của PDF. Bản vẽ A3 ~ 2384x1684pt.
WIRE_SNAP_TOLERANCE = 3.0      # gộp 2 đầu dây gần nhau thành 1 nút mạng
OBJECT_ATTACH_TOLERANCE = 55.0  # khoảng cách tối đa từ đối tượng tới mạng dây để coi là nối
MIN_WIRE_LENGTH = 1.0          # bỏ các đoạn quá ngắn (nhiễu)

# --- Phase 2: sheet classifier ---
# Phân loại dựa trên TIÊU ĐỀ trong title block (mạnh hơn nhiều so với đếm full-text,
# vì legend/ký hiệu lặp lại trên mọi sheet).
SHEET_KEYWORDS: dict[str, list[str]] = {
    "single_line": ["SINGLE LINE", "RISER DIAGRAM", "SƠ ĐỒ NGUYÊN LÝ", "SCHEMATIC"],
    "panel_schedule": ["PANEL SCHEDULE", "BẢNG TẢI", "LOAD SCHEDULE"],
    "schedule": ["SCHEDULE", "BẢNG THỐNG KÊ"],
    "legend": ["LEGEND", "KÝ HIỆU", "SYMBOL LIST"],
    "lighting_layout": ["LIGHTING LAYOUT", "LIGHTING PLAN", "CHIẾU SÁNG"],
    "power_layout": ["POWER LAYOUT", "POWER SUPPLY", "POWER PLAN", "CẤP NGUỒN", "Ổ CẮM"],
    "mechanical": ["MECHANICAL", "HVAC", "VENTILATION", "ĐIỀU HÒA", "THÔNG GIÓ"],
    "plumbing": ["PLUMBING", "WATER SUPPLY", "DRAINAGE", "SANITARY",
                 "CẤP NƯỚC", "THOÁT NƯỚC", "CẤP THOÁT NƯỚC"],
}

# Vùng title block (tỉ lệ theo trang) để trích tiêu đề sheet.
TITLE_BLOCK_REGION = (0.60, 0.60, 1.0, 1.0)  # (x1,y1,x2,y2) chuẩn hoá
