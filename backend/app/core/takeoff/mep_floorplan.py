"""KIỂU MEP — Mặt bằng phối hợp cơ điện (combine), phần THANG–MÁNG CÁP điện.

Bản vẽ này KHÁC HẲN sơ đồ nguyên lý tủ điện (SLD):
  - Là mặt bằng (floor plan), hàng trăm nghìn nét vẽ, KHÔNG có layer CAD, không
    color-code theo hệ → không thể tách hệ như SLD.
  - Mỗi hệ thống M&E được chú thích bằng TAG chữ đặt ở đầu nhãn dẫn (leader).

Phạm vi (đã chốt): chỉ bóc INVENTORY hệ ĐIỆN = thang–máng cáp, KHÔNG đo chiều dài.
  - LV_TK / LV_TR / ELV: máng/trunking, tag dạng  HỆ-LOẠI-RỘNGxCAO-BOT=FFL+caođộ
        vd  LV_TK-TK-200x50-BOT=FFL+2750
  - THANG-<mã>: thang cáp, chỉ có mã tham chiếu (không kích thước inline)
        vd  THANG-12, THANG-1A

Mỗi tag là MỘT callout, không phải một tuyến vật lý. Vì vậy đầu ra là "danh sách
quy cách + số lần callout (qty)", KHÔNG phải chiều dài/số lượng tuyến thực tế.
"""
from __future__ import annotations

import re
from collections import OrderedDict

import fitz

from .base import TakeoffItem, TakeoffResult, collect_words

# HỆ-LOẠI-RỘNGxCAO[-BOT=FFL+caođộ]  (vd LV_TK-TK-200x50-BOT=FFL+2750)
#
# Mã hệ KHÔNG liệt kê cứng theo một bộ hồ sơ (LV_TK/LV_TR/ELV) mà nhận theo DẠNG mã
# hệ ĐIỆN: LV/MV/EL/ELV/PWR + hậu tố tuỳ ý. Vẫn phải gác bằng danh sách này chứ
# không cho mã hệ bất kỳ, vì mặt bằng phối hợp còn tag của hệ KHÁC cùng dạng
# "HỆ-LOẠI-RỘNGxCAO" (ống gió SAD-DUCT-600x300...) — bóc vào là sai phạm vi (chỉ hệ điện).
_ELEC_SYS_RE = re.compile(r"^(?:LV|MV|EL|ELV|PWR)(?:[_-][A-Z0-9]{1,4})?$", re.IGNORECASE)
# Cao độ để tuỳ chọn: bộ hồ sơ khác có thể ghi cao độ ở nơi khác hoặc không ghi.
_TRAY_RE = re.compile(
    r"^(?P<sys>[A-Z][A-Z0-9_]{0,7})-(?P<kind>[A-Z]+)-"
    r"(?P<w>\d+)x(?P<h>\d+)(?:-BOT=FFL\+(?P<elev>\d+))?",
    re.IGNORECASE,
)
# <hệ thang>-<mã> (mã tham chiếu thang cáp, không có kích thước)
_LADDER_SYS = ("THANG", "LADDER", "TCA")
_LADDER_RE = re.compile(rf"^(?P<sys>{'|'.join(_LADDER_SYS)})-(?P<ref>\w+)$", re.IGNORECASE)
# GCC-RỘNGxCAO: nghi là giếng kỹ thuật, KHÔNG chắc là điện -> chỉ log, không bóc
_GCC_RE = re.compile(r"^GCC-\d+[xX]\d+", re.IGNORECASE)

_SYS_NAME = {
    "LV_TK": "Máng cáp hạ thế",
    "LV_TR": "Máng/trunking hạ thế",
    "ELV":   "Máng cáp điện nhẹ (ELV)",
    "THANG": "Thang cáp",
}
# Tên hệ cho mã chưa có trong bảng trên — suy theo tiền tố cấp điện áp.
_SYS_PREFIX_NAME = (
    ("ELV", "Máng cáp điện nhẹ (ELV)"),
    ("LV", "Máng cáp hạ thế"),
    ("MV", "Máng cáp trung thế"),
    ("PWR", "Máng cáp động lực"),
    ("EL", "Máng cáp điện"),
)


def _sys_name(sys: str) -> str:
    if sys in _SYS_NAME:
        return _SYS_NAME[sys]
    if sys in _LADDER_SYS:
        return _SYS_NAME["THANG"]
    for pre, name in _SYS_PREFIX_NAME:
        if sys.startswith(pre):
            return name
    return sys


def _tray_match(text: str):
    """Tag máng/trunking của hệ ĐIỆN? (đã gác mã hệ + loại trừ giếng kỹ thuật GCC)"""
    if _GCC_RE.match(text):
        return None
    m = _TRAY_RE.match(text)
    return m if m and _ELEC_SYS_RE.match(m.group("sys")) else None


def detect_score(page: fitz.Page) -> float:
    """Điểm khả năng là mặt bằng MEP (phần điện): đếm tag thang–máng cáp."""
    n = 0
    for w in collect_words(page):
        if _tray_match(w.text) or _LADDER_RE.match(w.text):
            n += 1
    return n


def extract(page: fitz.Page, page_index: int) -> TakeoffResult:
    res = TakeoffResult(page=page_index, diagram_type="mep_tray")
    words = collect_words(page)

    # Gom theo khoá để đếm số callout (giữ thứ tự gặp đầu tiên cho ổn định).
    groups: "OrderedDict[tuple, dict]" = OrderedDict()
    gcc_ignored: list[str] = []

    for w in words:
        t = w.text
        m = _tray_match(t)
        if m:
            sys = m.group("sys").upper()
            size = f"{m.group('w')}x{m.group('h')}"
            elev = f"BOT=FFL+{m.group('elev')}" if m.group("elev") else ""
            key = (sys, size, elev)
            g = groups.setdefault(key, {"sys": sys, "size": size, "elev": elev,
                                        "ref": "", "count": 0})
            g["count"] += 1
            continue
        m = _LADDER_RE.match(t)
        if m:
            sys = m.group("sys").upper()
            ref = m.group("ref").upper()
            key = (sys, ref)
            g = groups.setdefault(key, {"sys": sys, "size": "", "elev": "",
                                        "ref": ref, "count": 0})
            g["count"] += 1
            continue
        if _GCC_RE.match(t):
            gcc_ignored.append(t)

    for g in groups.values():
        res.items.append(TakeoffItem(
            roadName=g["sys"],
            loadName=_sys_name(g["sys"]),
            size=g["size"],
            cableSpec=g["elev"],
            conduit=g["ref"],
            itemGroup="Thang máng cáp",
            itemName=g["sys"],
            qty=g["count"],
        ))

    n_tray = sum(g["count"] for g in groups.values() if g["sys"] not in _LADDER_SYS)
    n_ladder = sum(g["count"] for g in groups.values() if g["sys"] in _LADDER_SYS)
    systems: "OrderedDict[str, int]" = OrderedDict()
    for g in groups.values():
        systems[g["sys"]] = systems.get(g["sys"], 0) + g["count"]
    res.debug = {
        "n_tray": n_tray,
        "n_ladder": n_ladder,
        "n_groups": len(groups),
        "systems": dict(systems),
        "gcc_ignored": sorted(set(gcc_ignored)),
    }
    return res
