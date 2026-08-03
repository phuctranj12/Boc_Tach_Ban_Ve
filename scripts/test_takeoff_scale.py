#!/usr/bin/env python3
"""Kiểm thử BẤT BIẾN TỶ LỆ & HƯỚNG của bóc tách (chạy thẳng trên core, không cần server).

Vì sao cần: mọi extractor đều calibrate ngưỡng khoảng cách trên MỘT bản vẽ chuẩn rồi
nhân theo tỷ lệ đo được trên trang. Nếu phép đo tỷ lệ đó sai, lỗi KHÔNG lộ ra ở bản vẽ
gốc — chỉ lộ khi khách gửi bản vẽ xuất ở tỷ lệ khác (tách 1 tủ ra khổ giấy riêng) hoặc
bị xoay. Script này dựng đúng hai tình huống đó rồi so với kết quả ở tỷ lệ 1, hướng 0.

Cách dùng:
    python3 scripts/test_takeoff_scale.py           # quét trong DẢI HỖ TRỢ, phải PASS hết
    python3 scripts/test_takeoff_scale.py --full    # quét cả ngoài dải (chỉ báo, không FAIL)

Thoát mã 0 nếu tất cả PASS.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

import fitz  # noqa: E402

from app.core.takeoff import extract_takeoff  # noqa: E402

TYPES = os.path.join(ROOT, "types")

# (file, trang, kiểu sơ đồ, dải tỷ lệ ĐÃ KIỂM CHỨNG cho kiểu đó)
#
# Dải là KẾT QUẢ ĐO, không phải mong muốn. Hai chỗ hụt và lý do:
#   - busbar_slash chỉ tới 3x: sld_extractor.py (module cũ) tự đo tỷ lệ bằng chiều cao
#     chữ, mà từ ~5x chữ thân bài của bản vẽ này vượt mốc lọc 40px trong khi chữ nhỏ
#     còn sót vẫn họp thành cụm "trông bình thường" → đo hụt ~20% → dư 1 dòng.
#   - cdc_elv_unit từ 0.5x: dưới mức đó, nếu trang ĐỒNG THỜI bị xoay 90° thì các dòng
#     cáp rụng bớt trước khi kịp dóng phòng đích.
CASES = [
    ("type1.pdf", 0, "busbar_slash", 0.25, 3.0),
    ("type2.pdf", 0, "panel_table", 0.25, 5.0),
    ("type3.pdf", 0, "hotel_db", 0.25, 5.0),
    ("02.DIEN NHE.pdf", 23, "cdc_elv_unit", 0.5, 5.0),
]
SCALES = (0.25, 0.3, 0.5, 0.75, 1.1, 1.5, 2.0, 3.0, 5.0)
ROTS = (0, 90, 180, 270)

_G, _R, _Y, _0 = "\033[32m", "\033[31m", "\033[33m", "\033[0m"
_passed = _failed = _info = 0


def _report(ok: bool, msg: str, in_envelope: bool = True) -> None:
    """Ngoài dải hỗ trợ thì chỉ BÁO, không tính FAIL — để dải được nới ra một cách
    có bằng chứng: khi nào một mốc ngoài dải xanh ổn định thì mới sửa CASES."""
    global _passed, _failed, _info
    if not in_envelope:
        _info += 1
        print(f"{_Y}····{_0} {msg}  (ngoài dải hỗ trợ)")
    elif ok:
        _passed += 1
        print(f"{_G}PASS{_0} {msg}")
    else:
        _failed += 1
        print(f"{_R}FAIL{_0} {msg}")


def replot(page: fitz.Page, k: float, rot: int = 0):
    """Vẽ lại trang ở tỷ lệ k và xoay rot — vẫn là vector, đúng như bản vẽ được xuất
    lại ở khổ giấy/tỷ lệ plot khác. Doc tạm phải giữ sống tới khi dùng xong."""
    r = page.rect
    w, h = r.width * k, r.height * k
    out = fitz.open()
    np = out.new_page(width=h if rot in (90, 270) else w,
                      height=w if rot in (90, 270) else h)
    np.show_pdf_page(np.rect, page.parent, page.number, rotate=rot)
    return out, np


def rows(page: fitz.Page, idx: int) -> tuple[str, list]:
    res = extract_takeoff(page, idx)
    return res.diagram_type, [tuple(it.to_dict().values()) for it in res.items]


def main() -> int:
    full = "--full" in sys.argv
    for name, pi, want_type, kmin, kmax in CASES:
        path = os.path.join(TYPES, name)
        if not os.path.exists(path):
            _report(False, f"{name}: thiếu file mẫu")
            continue
        doc = fitz.open(path)
        # Mốc so sánh = chính trang đó vẽ lại ở tỷ lệ 1 (loại nhiễu do vẽ lại).
        hold, p1 = replot(doc[pi], 1.0, 0)
        base_type, base = rows(p1, pi)
        hold.close()
        _report(base_type == want_type and bool(base),
                f"{name} p{pi+1}: mốc = {base_type}, {len(base)} dòng "
                f"(dải hỗ trợ {kmin}x–{kmax}x)")

        for rot in ROTS:
            for k in SCALES:
                inside = kmin <= k <= kmax
                if not inside and not full:
                    continue
                hold, p = replot(doc[pi], k, rot)
                try:
                    got_type, got = rows(p, pi)
                finally:
                    hold.close()
                ok = (got_type == base_type and got == base)
                _report(ok, f"{name} p{pi+1}: tỷ lệ {k}x, xoay {rot}° → "
                            f"{got_type}, {len(got)} dòng"
                            + ("" if ok else f"  ≠ mốc {base_type}/{len(base)} dòng"),
                        inside)
        doc.close()

    print(f"\nTổng: {_passed} PASS / {_failed} FAIL"
          + (f" / {_info} ngoài dải" if _info else ""))
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
