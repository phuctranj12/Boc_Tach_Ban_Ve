"""Trích THÔNG TIN HÀNH CHÍNH của từng trang bản vẽ (dự án, tháp/hầm, khu vực,
tầng, mã điển hình).

Đây là lớp BỔ SUNG, hoàn toàn tách khỏi logic bóc khối lượng: không extractor nào
phải sửa, không ngưỡng nào thay đổi. `extract_meta(page)` luôn trả về đủ 5 khoá;
khoá nào không đọc được thì để chuỗi rỗng cho người dùng tự điền trên giao diện.

Nguyên tắc: THÀ ĐỂ TRỐNG CÒN HƠN ĐIỀN SAI. Giá trị chỉ được điền khi bản vẽ cho
bằng chứng rõ ràng và KHÔNG mâu thuẫn trong cùng một trang.

Khảo sát trên 3 loại bản vẽ thật (43 trang) — cơ sở của các luật dưới đây:
  * type1 (14 trang, layout căn hộ) — có title block đầy đủ ở góc dưới-phải:
        "LÔ CCCT-02" / "PLOT CCCT-02"      -> dự án/hạng mục
        "TYPICAL 2BR(+) - TYPE C"          -> mã điển hình
    Mỗi trang một mã điển hình khác nhau (2BR-TYPE C/D/E/F/G, 2BR(+)-A..F,
    3BR(+)-A..C) nên PHẢI giữ cả chữ loại; cắt còn "2BR" sẽ làm 5 trang trùng nhau.
  * type2 (sơ đồ tủ) và type3 (SLD khách sạn) — KHÔNG có title block. Tầng/khu vực
    nằm rải rác theo TỪNG TỦ, một trang có nhiều tầng (type3 p2 có tầng 3/4/5/6),
    nên không có giá trị nào đại diện được cho cả trang -> để trống.
  * Tháp/hầm: không bản vẽ nào trong 3 loại có dữ liệu này -> luôn để trống, chờ
    gặp bản vẽ thật có rồi mới viết luật (không đoán bằng regex mò).
"""
from __future__ import annotations

import re

import fitz

from ..page_text import text_dict

# 5 trường, theo đúng thứ tự hiển thị. Luôn có mặt trong JSON dù rỗng.
META_FIELDS = ("project", "towerOrBasement", "area", "floor", "typicalCode")

# Vùng title block: mép phải-dưới. Đo trên type1 (2384x1684): các dòng cần lấy đều
# nằm ở x > 0.80W, y > 0.60H.
_TITLE_REGION = (0.80, 0.60)

# Giữ nguyên cụm như in trên bản vẽ ("LÔ CCCT-02"), không cắt bớt tiền tố.
# Title block song ngữ in cả "LÔ ..." và "PLOT ..." — ưu tiên bản tiếng Việt vì
# toàn bộ giao diện và BOQ dùng tiếng Việt.
_PROJECT_RES = (
    re.compile(r"^(LÔ\s+.+)$", re.IGNORECASE),
    re.compile(r"^(PLOT\s+.+)$", re.IGNORECASE),
)
_TYPICAL_RE = re.compile(r"\bTYPICAL\s+(.+)$", re.IGNORECASE)
_FLOOR_RE = re.compile(r"(?:TẦNG|LEVEL|FLOOR)\s*(\d{1,2}|HẦM\s*\d?)", re.IGNORECASE)

# ---------- Khung tên kiểu CDC (bộ hồ sơ 01.DIEN / 02.DIEN NHE / 05.DIEN DH) ----------
# Dạng "NHÃN - LABEL :" cỡ ~7pt, giá trị cỡ >=9pt nằm ngay bên dưới. Ví dụ:
#     DỰ ÁN - PROJECT :          KHU ĐÔ THỊ MỚI TÂY MỖ - ĐẠI MỖ
#     HẠNG MỤC - ITEM :          PHẦN THÂN F2-HH01-U39 (D1)
#     TÊN BẢN VẼ - DWG TITLE :   MẶT BẰNG CẤP ĐIỆN & BỐ TRÍ Ổ CẮM | TẦNG 1
# Khung tên này rộng hơn kiểu type1 nên vùng quét phải nới sang trái.
_TITLE_REGION_CDC = (0.75, 0.55)
_CDC_VALUE_MIN_SIZE = 9.0     # giá trị luôn to hơn nhãn (~7.1pt)
_CDC_VALUE_MAX_DY = 60.0      # giá trị nằm sát ngay dưới nhãn
_CDC_VALUE_MAX_DX = 40.0      # ...và cùng cột với nhãn (chống chữ bản vẽ lấn vào)

_CDC_LABELS = {
    "project": "DỰ ÁN",
    "building": "CÔNG TRÌNH",
    "item": "HẠNG MỤC",
    "title": "TÊN BẢN VẼ",
}

# Tầng lấy từ tên bản vẽ: "TẦNG 1", "TẦNG 2 - 4", "TẦNG 15~19, 21~39",
# "TẦNG KỸ THUẬT MÁI", "TẦNG VĂN PHÒNG ĐIỂN HÌNH"…
_CDC_FLOOR_RE = re.compile(r"(TẦNG\s+[^|]+?)\s*$", re.IGNORECASE)
# Mã căn hộ điển hình: CH01, CH05A, CH30…
_CDC_UNIT_RE = re.compile(r"\bCĂN\s+HỘ\s+(CH\d+[A-Z]?)\b", re.IGNORECASE)
# Khối/khu vực: "- KHỐI VĂN PHÒNG", "- KHỐI THƯƠNG MẠI DỊCH VỤ, CĂN HỘ"
_CDC_BLOCK_RE = re.compile(r"(KHỐI\s+[^|]+?)\s*$", re.IGNORECASE)


def _lines(page: fitz.Page) -> list[tuple[float, float, str]]:
    """(x, y, text) của mọi dòng text trên trang — dùng chung cache parse."""
    out = []
    for b in text_dict(page)["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"]).strip()
            if t:
                bb = l["bbox"]
                out.append((bb[0], bb[1], t))
    return out


def _sized_lines(page: fitz.Page) -> list[tuple[float, float, float, str]]:
    """(y, x, cỡ_chữ, text) trong vùng title block, đã sắp theo thứ tự đọc.

    Khung tên kiểu CDC in NHÃN cỡ nhỏ rồi GIÁ TRỊ cỡ lớn ngay bên dưới, nên phải
    biết cỡ chữ mới tách được nhãn khỏi giá trị.
    """
    fx, fy = _TITLE_REGION_CDC
    xmin, ymin = fx * page.rect.width, fy * page.rect.height
    out = []
    for b in text_dict(page)["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"]).strip()
            bb = l["bbox"]
            if t and bb[0] > xmin and bb[1] > ymin:
                out.append((bb[1], bb[0], max(s["size"] for s in l["spans"]), t))
    out.sort()
    return out


def _title_lines(page: fitz.Page, lines) -> list[str]:
    fx, fy = _TITLE_REGION
    xmin, ymin = fx * page.rect.width, fy * page.rect.height
    return [t for x, y, t in lines if x > xmin and y > ymin]


def _first_match(rx: re.Pattern, texts) -> str:
    for t in texts:
        m = rx.search(t)
        if m:
            return m.group(1).strip()
    return ""


def _unique_floor(lines) -> str:
    """Tầng của trang — CHỈ điền khi cả trang có đúng MỘT giá trị.

    type3 có trang chứa tủ ở tầng 3, 4, 5, 6 cùng lúc; gán một tầng cho cả trang
    sẽ ghi sai vào BOQ nên trường hợp đó trả rỗng để người dùng tự quyết.
    """
    vals = set()
    for _, _, t in lines:
        for m in _FLOOR_RE.finditer(t):
            vals.add(re.sub(r"\s+", " ", m.group(1).strip().upper()))
    return vals.pop() if len(vals) == 1 else ""


def _cdc_values(page: fitz.Page) -> dict:
    """Đọc khung tên kiểu CDC: {khoá logic -> giá trị}. Rỗng nếu không phải kiểu này.

    Neo theo NHÃN: tìm dòng bắt đầu bằng nhãn, rồi gom các dòng cỡ chữ lớn nằm ngay
    bên dưới cho tới khi gặp dòng nhỏ tiếp theo (= nhãn kế) hoặc cách quá xa.
    """
    rows = _sized_lines(page)
    out: dict[str, str] = {}
    for i, (y, x, _sz, t) in enumerate(rows):
        up = t.upper()
        # Nhãn CDC luôn kết thúc bằng ':' ("DỰ ÁN - PROJECT :"). Điều kiện này tách
        # hẳn khỏi khung tên type1 ("TÊN BẢN VẼ/ DRAWING NAME" — dấu '/', không ':'),
        # nếu thiếu thì type1 sẽ rơi nhầm vào nhánh CDC và mất hết dữ liệu.
        if not t.rstrip().endswith(":"):
            continue
        for key, label in _CDC_LABELS.items():
            if key in out or not up.startswith(label):
                continue
            vals = []
            for y2, x2, sz2, t2 in rows[i + 1:]:
                if y2 - y > _CDC_VALUE_MAX_DY:
                    break
                # Giá trị nằm cùng CỘT với nhãn. Không có ràng buộc này thì chữ của
                # bản vẽ lấn vào vùng khung tên sẽ bị gom nhầm (vd 'P. NGỦ' của mặt
                # bằng căn hộ ở x=1837 trong khi cột khung tên ở x≈2140).
                if x2 < x - _CDC_VALUE_MAX_DX:
                    continue
                if sz2 >= _CDC_VALUE_MIN_SIZE:
                    vals.append(t2)
                elif vals:
                    break        # đã sang nhãn kế tiếp
            if vals:
                out[key] = " ".join(vals)
    return out


def _extract_meta_cdc(cdc: dict) -> dict:
    """Ánh xạ khung tên CDC sang 5 trường chuẩn."""
    title = cdc.get("title", "")
    floor = ""
    m = _CDC_FLOOR_RE.search(title)
    if m:
        floor = re.sub(r"\s+", " ", m.group(1)).strip()
    area = ""
    m = _CDC_BLOCK_RE.search(title)
    if m:
        area = re.sub(r"\s+", " ", m.group(1)).strip().lstrip("- ")
    typical = ""
    m = _CDC_UNIT_RE.search(title)
    if m:
        typical = m.group(1).upper()
    return {
        "project": cdc.get("project", ""),
        # HẠNG MỤC của bộ hồ sơ này là mã khối/tháp ("PHẦN THÂN F2-HH01-U39 (D1)").
        # Đây là suy đoán hợp lý nhất cho trường tháp/hầm — người dùng sửa lại được.
        "towerOrBasement": cdc.get("item", ""),
        "area": area,
        "floor": floor,
        "typicalCode": typical,
    }


def extract_meta(page: fitz.Page) -> dict:
    """Trả về dict đủ 5 khoá META_FIELDS; khoá không đọc được = "" (để trống)."""
    cdc = _cdc_values(page)
    if cdc.get("title") or cdc.get("project"):
        return _extract_meta_cdc(cdc)

    lines = _lines(page)
    title = _title_lines(page, lines)
    project = ""
    for rx in _PROJECT_RES:          # thử tiếng Việt trước, rồi mới tới tiếng Anh
        project = _first_match(rx, title)
        if project:
            break
    return {
        "project": project,
        # Chưa có bản vẽ mẫu nào chứa thông tin tháp/hầm -> để người dùng tự điền.
        "towerOrBasement": "",
        # Khu vực chỉ có ở cấp TỪNG TỦ (type3), không có giá trị cho cả trang.
        "area": "",
        "floor": _unique_floor(lines),
        "typicalCode": _first_match(_TYPICAL_RE, title),
    }


# ---------- Phân loại trang theo TÊN BẢN VẼ ----------
# Suy ra vai trò của trang để định tuyến extractor và bỏ qua trang không phải nguồn
# BOQ. Khớp theo thứ tự — cụm cụ thể đặt trước cụm chung.
_SHEET_ROLES = [
    ("index",        ("DANH MỤC BẢN VẼ",)),
    ("legend",       ("KÝ HIỆU CHUNG", "KÝ HIỆU")),
    ("detail",       ("CHI TIẾT LẮP ĐẶT", "CHI TIẾT")),
    ("unit_layout",  ("BỐ TRÍ ĐIỆN CĂN HỘ", "BỐ TRÍ ĐIỆN NHẸ CĂN HỘ")),
    ("control",      ("SƠ ĐỒ ĐIỀU KHIỂN", "SƠ ĐỒ ĐIỀU KIỂN",
                      "BẢNG THEO DÕI", "BẢNG ĐIỂM ĐIỀU KHIỂN")),
    ("power_sld",    ("SƠ ĐỒ PHÂN PHỐI ĐIỆN", "SƠ ĐỒ CẤP ĐIỆN")),
    ("elv_riser",    ("SƠ ĐỒ HỆ THỐNG",)),
    ("floor_plan",   ("MẶT BẰNG",)),
]

# Trang không chứa khối lượng để bóc -> bỏ qua, không cần báo lỗi.
NON_BOQ_ROLES = {"index", "legend", "detail"}


def sheet_role(page: fitz.Page) -> str:
    """Vai trò của trang suy từ tên bản vẽ trong khung tên. '' nếu không đọc được."""
    title = _cdc_values(page).get("title", "").upper()
    if not title:
        return ""
    for role, keys in _SHEET_ROLES:
        if any(k in title for k in keys):
            return role
    return "other"


def blank_meta() -> dict:
    """Bản rỗng đủ 5 khoá — dùng khi không có trang để trích (dữ liệu đã lưu cũ)."""
    return {k: "" for k in META_FIELDS}


def normalize_meta(raw) -> dict:
    """Chuẩn hoá meta do client gửi lên: đủ khoá, chuỗi, đã strip, bỏ khoá lạ."""
    src = raw if isinstance(raw, dict) else {}
    return {k: str(src.get(k) or "").strip() for k in META_FIELDS}
