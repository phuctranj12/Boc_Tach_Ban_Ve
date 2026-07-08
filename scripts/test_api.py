#!/usr/bin/env python3
"""Script test API bóc tách bản vẽ — bám theo API_DOCS.md.

Chạy qua LẦN LƯỢT mọi endpoint trong tài liệu và báo PASS/FAIL từng bước.

Cách dùng:
    python scripts/test_api.py                         # test Space mặc định + PDF mẫu
    python scripts/test_api.py <BASE_URL> <PDF>        # chỉ định server + file
    API_BASE=http://localhost:8000 python scripts/test_api.py   # test bản chạy local

Yêu cầu:  pip install requests
Thoát mã 0 nếu tất cả PASS, khác 0 nếu có FAIL.
"""
from __future__ import annotations

import os
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("Thiếu thư viện 'requests'. Cài bằng:  pip install requests")

# ---- Cấu hình: đọc từ tham số dòng lệnh hoặc biến môi trường ----
DEFAULT_BASE = "https://tranphuc120203-boc-tach-ban-ve.hf.space"
DEFAULT_PDF = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Sơ đồ nguyên lý loại 2.pdf",
)
BASE = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("API_BASE", DEFAULT_BASE)).rstrip("/")
PDF = sys.argv[2] if len(sys.argv) > 2 else os.getenv("API_PDF", DEFAULT_PDF)

# 8 trường bắt buộc của 1 dòng khối lượng (theo API_DOCS.md mục 4).
ITEM_FIELDS = {"panelName", "roadName", "loadName", "itemGroup",
               "itemName", "size", "cableSpec", "conduit"}

# ---- Tiện ích in kết quả ----
_G, _R, _Y, _0 = "\033[32m", "\033[31m", "\033[33m", "\033[0m"
_passed = _failed = 0


def ok(name: str, detail: str = "") -> None:
    global _passed
    _passed += 1
    print(f"  {_G}✓ PASS{_0} {name}" + (f"  {_Y}{detail}{_0}" if detail else ""))


def fail(name: str, detail: str = "") -> None:
    global _failed
    _failed += 1
    print(f"  {_R}✗ FAIL{_0} {name}" + (f"  → {detail}" if detail else ""))


def get(path: str, **kw):
    return requests.get(BASE + path, timeout=kw.pop("timeout", 60), **kw)


def post(path: str, **kw):
    return requests.post(BASE + path, timeout=kw.pop("timeout", 180), **kw)


def wait_awake(retries: int = 6) -> bool:
    """Space free ngủ khi lâu không dùng — chờ nó thức (cold start 20–60s)."""
    for i in range(retries):
        try:
            r = get("/api/health", timeout=30)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        print(f"    … server chưa sẵn sàng, chờ 10s (lần {i + 1}/{retries})")
        time.sleep(10)
    return False


def main() -> int:
    print(f"\n=== TEST API ===\nBASE = {BASE}\nPDF  = {PDF}\n")
    if not os.path.isfile(PDF):
        return int(bool(fail("Tồn tại file PDF để test", f"không thấy: {PDF}") or 1))

    # 0) health + cold start
    print("[0] Health / cold start")
    if not wait_awake():
        fail("GET /api/health", "server không phản hồi sau nhiều lần thử")
        return _summary()
    ok("GET /api/health")

    # 1) POST /api/analyze
    print("\n[1] POST /api/analyze (upload PDF)")
    with open(PDF, "rb") as f:
        r = post("/api/analyze", files={"file": (os.path.basename(PDF), f, "application/pdf")})
    if r.status_code != 200:
        fail("POST /api/analyze", f"HTTP {r.status_code}: {r.text[:200]}")
        return _summary()
    data = r.json()
    job_id = data.get("job_id", "")
    if job_id:
        ok("POST /api/analyze", f"job_id={job_id}, page_count={data.get('page_count')}")
    else:
        fail("POST /api/analyze", "thiếu job_id trong response")
        return _summary()
    for key in ("job_id", "filename", "page_count", "sheets", "stats"):
        (ok if key in data else fail)(f"response.analyze có '{key}'")
    n_pages = data.get("page_count", 0)

    # 2) GET /api/results/{job}
    print("\n[2] GET /api/results/{job_id}")
    r = get(f"/api/results/{job_id}")
    (ok if r.status_code == 200 and r.json().get("job_id") == job_id
     else fail)("GET /api/results/{job_id}", f"HTTP {r.status_code}")

    # 3) GET /sld?page=0  — bóc tách 1 trang
    print("\n[3] GET /api/results/{job_id}/sld?page=0")
    r = get(f"/api/results/{job_id}/sld", params={"page": 0, "kind": "auto"})
    if r.status_code == 200:
        d = r.json()
        ok("GET /sld", f"diagramType={d.get('diagramType')}, items={len(d.get('items', []))}")
        items = d.get("items", [])
        if items:
            missing = ITEM_FIELDS - set(items[0].keys())
            (ok if not missing else fail)("item có đủ 8 trường schema",
                                          "" if not missing else f"thiếu {missing}")
        for key in ("page", "diagramType", "items", "panels"):
            (ok if key in d else fail)(f"response.sld có '{key}'")
    else:
        fail("GET /sld", f"HTTP {r.status_code}: {r.text[:150]}")

    # 4) GET /review/{page}  — dữ liệu 1 trang (bóc tự động nếu chưa lưu)
    print("\n[4] GET /api/results/{job_id}/review/0")
    r = get(f"/api/results/{job_id}/review/0")
    (ok if r.status_code == 200 and "items" in r.json()
     else fail)("GET /review/0", f"HTTP {r.status_code}")

    # 5) PUT /review/{page}  — lưu chỉnh sửa (kiểm tra ghi được)
    print("\n[5] PUT /api/results/{job_id}/review/0 (lưu nháp)")
    r0 = get(f"/api/results/{job_id}/review/0").json()
    payload = {"diagramType": r0.get("diagramType", ""),
               "panelName": r0.get("panelName", ""),
               "panels": r0.get("panels", []),
               "items": r0.get("items", []),
               "confirmed": False}
    r = requests.put(f"{BASE}/api/results/{job_id}/review/0", json=payload, timeout=60)
    (ok if r.status_code == 200 else fail)("PUT /review/0", f"HTTP {r.status_code}")

    # 6) POST confirm-all
    print("\n[6] POST /api/results/{job_id}/review/confirm-all")
    r = post(f"/api/results/{job_id}/review/confirm-all")
    if r.status_code == 200:
        ok("POST confirm-all", f"confirmed_pages={r.json().get('confirmed_pages')}")
    else:
        fail("POST confirm-all", f"HTTP {r.status_code}: {r.text[:150]}")

    # 7) GET /review  — trạng thái duyệt
    print("\n[7] GET /api/results/{job_id}/review (trạng thái)")
    r = get(f"/api/results/{job_id}/review")
    (ok if r.status_code == 200 and isinstance(r.json(), list)
     else fail)("GET /review", f"HTTP {r.status_code}")

    # 8) GET export.json
    print("\n[8] GET /api/results/{job_id}/export.json?confirmed=true")
    r = get(f"/api/results/{job_id}/export.json", params={"confirmed": "true"})
    if r.status_code == 200 and isinstance(r.json(), list):
        rows = r.json()
        ok("GET export.json", f"{len(rows)} dòng BOQ")
        if rows:
            missing = ITEM_FIELDS - set(rows[0].keys())
            (ok if not missing else fail)("dòng BOQ có đủ 8 trường",
                                          "" if not missing else f"thiếu {missing}")
    else:
        fail("GET export.json", f"HTTP {r.status_code}")

    # 9) GET export.xlsx
    print("\n[9] GET /api/results/{job_id}/export.xlsx?confirmed=true")
    r = get(f"/api/results/{job_id}/export.xlsx", params={"confirmed": "true"})
    ctype = r.headers.get("content-type", "")
    (ok if r.status_code == 200 and "spreadsheet" in ctype
     else fail)("GET export.xlsx", f"HTTP {r.status_code}, {len(r.content)} bytes")

    # 10) GET preview PNG
    print("\n[10] GET /api/results/{job_id}/page/0/preview")
    r = get(f"/api/results/{job_id}/page/0/preview", params={"scale": 1.0})
    (ok if r.status_code == 200 and r.headers.get("content-type") == "image/png"
     else fail)("GET preview", f"HTTP {r.status_code}, {len(r.content)} bytes PNG")

    # 11) GET qa
    print("\n[11] GET /api/results/{job_id}/qa")
    r = get(f"/api/results/{job_id}/qa", params={"q": "tong cong suat den"})
    (ok if r.status_code == 200 and "answer" in r.json()
     else fail)("GET qa", f"HTTP {r.status_code}")

    # 12) Kiểm tra mã lỗi theo tài liệu
    print("\n[12] Mã lỗi (theo API_DOCS.md mục 6)")
    r = get(f"/api/results/khong-ton-tai-xyz")
    (ok if r.status_code == 404 else fail)("job_id sai → 404", f"HTTP {r.status_code}")
    r = get(f"/api/results/{job_id}/sld", params={"page": 9999})
    (ok if r.status_code == 404 else fail)("page vượt giới hạn → 404", f"HTTP {r.status_code}")

    return _summary()


def _summary() -> int:
    total = _passed + _failed
    color = _G if _failed == 0 else _R
    print(f"\n{'=' * 40}\n{color}KẾT QUẢ: {_passed}/{total} PASS, {_failed} FAIL{_0}\n")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
