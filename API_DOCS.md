# API Bóc tách bản vẽ — Tài liệu tích hợp

Cho phép hệ thống khác **gửi file PDF bản vẽ lên, xử lý tự động, rồi lấy về JSON khối
lượng cáp/ống (BOQ)** để đưa vào hệ thống của họ — không cần mở giao diện web.

- **Base URL:** `https://tranphuc120203-boc-tach-ban-ve.hf.space`
- **Xác thực:** Không (API mở). Ai có link đều gọi được.
- **Định dạng:** Request/response đều là JSON (trừ upload là `multipart/form-data`, và
  ảnh preview trả PNG, Excel trả file `.xlsx`).
- **CORS:** Mở (`*`) → gọi được trực tiếp từ trình duyệt/frontend khác.

> ⚠️ **Cold start:** Space chạy nền miễn phí, **ngủ khi lâu không dùng**. Request đầu
> tiên sau khi ngủ có thể mất **20–60s** để "thức dậy" (hoặc trả 503 → thử lại sau ít giây).
> Các request sau đó nhanh bình thường.

---

## 1. Luồng tích hợp khuyến nghị (headless, không cần sửa tay)

Chỉ **3 lời gọi** để đi từ file PDF → JSON khối lượng:

```
1) POST /api/analyze                              (upload PDF)      -> nhận job_id
2) POST /api/results/{job_id}/review/confirm-all  (bóc + chốt mọi trang)
3) GET  /api/results/{job_id}/export.json?confirmed=true            -> BOQ toàn dự án
```

- Bước 1 phân tích PDF, tạo `job_id` để tham chiếu ở các bước sau.
- Bước 2 tự động bóc tách **tất cả trang** có sơ đồ và đánh dấu "đã chốt".
- Bước 3 trả về **mảng JSON** gồm mọi dòng cáp/ống của toàn bộ dự án.

Nếu chỉ cần **1 trang**, có thể bỏ bước 2–3 và gọi thẳng
`GET /api/results/{job_id}/sld?page=0` (xem mục 3).

---

## 2. Ví dụ nhanh

### cURL
```bash
BASE="https://tranphuc120203-boc-tach-ban-ve.hf.space"

# 1) Upload -> lấy job_id
JOB=$(curl -s -F "file=@ban_ve.pdf" "$BASE/api/analyze" | python3 -c "import sys,json;print(json.load(sys.stdin)['job_id'])")

# 2) Bóc + chốt tất cả trang
curl -s -X POST "$BASE/api/results/$JOB/review/confirm-all"

# 3) Lấy BOQ JSON
curl -s "$BASE/api/results/$JOB/export.json?confirmed=true" -o BOQ.json
```

### Python (requests)
```python
import requests

BASE = "https://tranphuc120203-boc-tach-ban-ve.hf.space"

def boc_tach(pdf_path: str) -> list[dict]:
    # 1) Upload PDF
    with open(pdf_path, "rb") as f:
        r = requests.post(f"{BASE}/api/analyze",
                          files={"file": (pdf_path, f, "application/pdf")},
                          timeout=180)
    r.raise_for_status()
    job_id = r.json()["job_id"]

    # 2) Bóc + chốt mọi trang
    requests.post(f"{BASE}/api/results/{job_id}/review/confirm-all", timeout=180).raise_for_status()

    # 3) Lấy BOQ JSON
    r = requests.get(f"{BASE}/api/results/{job_id}/export.json",
                     params={"confirmed": "true"}, timeout=60)
    r.raise_for_status()
    return r.json()

rows = boc_tach("ban_ve.pdf")
print(len(rows), "dòng khối lượng")
for row in rows[:3]:
    print(row["roadName"], "|", row["size"], "|", row["cableSpec"])
```

### JavaScript (Node 18+ / trình duyệt)
```js
const BASE = "https://tranphuc120203-boc-tach-ban-ve.hf.space";

async function bocTach(file /* File hoặc Blob */) {
  const fd = new FormData();
  fd.append("file", file, "ban_ve.pdf");

  // 1) Upload
  const a = await fetch(`${BASE}/api/analyze`, { method: "POST", body: fd });
  const { job_id } = await a.json();

  // 2) Bóc + chốt
  await fetch(`${BASE}/api/results/${job_id}/review/confirm-all`, { method: "POST" });

  // 3) Lấy BOQ
  const r = await fetch(`${BASE}/api/results/${job_id}/export.json?confirmed=true`);
  return r.json(); // mảng dòng khối lượng
}
```

---

## 3. Tham chiếu endpoint

| Method | Đường dẫn | Công dụng |
|--------|-----------|-----------|
| GET  | `/api/health` | Kiểm tra server sống |
| POST | `/api/analyze` | Upload PDF, phân tích, tạo `job_id` |
| GET  | `/api/results/{job_id}` | Lấy lại kết quả phân tích của job |
| GET  | `/api/results/{job_id}/sld?page={n}&kind=auto` | **Bóc tách 1 trang** → JSON khối lượng |
| POST | `/api/results/{job_id}/review/confirm-all` | Bóc + chốt **tất cả** trang |
| GET  | `/api/results/{job_id}/review/{page}` | Lấy dữ liệu bóc 1 trang (bản đã lưu hoặc bóc tự động) |
| PUT  | `/api/results/{job_id}/review/{page}` | Lưu chỉnh sửa 1 trang (nếu muốn sửa trước khi xuất) |
| GET  | `/api/results/{job_id}/review` | Trạng thái duyệt từng trang |
| GET  | `/api/results/{job_id}/export.json?confirmed={bool}` | Xuất BOQ dạng JSON |
| GET  | `/api/results/{job_id}/export.xlsx?confirmed={bool}` | Xuất BOQ dạng Excel |
| GET  | `/api/results/{job_id}/qa?q={câu hỏi}` | Hỏi–đáp về quan hệ trong bản vẽ (rule-based) |
| GET  | `/api/results/{job_id}/page/{page}/preview?scale={n}` | Ảnh PNG render của 1 trang |

### `POST /api/analyze`
- **Body:** `multipart/form-data`, field `file` = 1 file `.pdf`.
- **Trả về** (rút gọn):
```json
{
  "job_id": "b727624b678e",
  "filename": "ban_ve.pdf",
  "page_count": 1,
  "sheets": [
    { "page": 0, "sheet_no": null, "sheet_type": "single_line",
      "title": null, "width": 2384, "height": 1684, "object_count": 0 }
  ],
  "stats": { "pages": 1, "nodes": 0, "by_sheet_type": { "single_line": 1 } }
}
```
- `job_id` dùng cho mọi lời gọi sau. `sheets[].sheet_type` cho biết loại từng trang
  (single_line, panel_schedule, lighting_layout, plumbing, …).
- Lỗi: `400` nếu không phải PDF; `500` nếu phân tích thất bại.

### `GET /api/results/{job_id}/sld?page={n}&kind=auto`
Bóc tách khối lượng của **1 trang**. `page` bắt đầu từ `0`. `kind=auto` (mặc định) tự
nhận diện loại sơ đồ; có thể ép loại bằng `kind=panel_table|busbar_slash|hotel_db|mep_tray`.
- **Trả về:**
```json
{
  "page": 0,
  "diagramType": "panel_table",
  "panelName": "",
  "panels": [ { "name": "TĐTM-1", "power": 0, "ptt": 0, "kdt": "" } ],
  "items": [
    {
      "panelName": "TĐTM-1",
      "roadName": "TĐTM-1",
      "loadName": "TỦ ĐIỆN SMARTHOME TẦNG 1",
      "itemGroup": "Dây & cáp điện",
      "itemName": "Dây/cáp Cu/PVC",
      "size": "6mm2",
      "cableSpec": "CU/PVC 3X(1X6MM2) +1X6MM2 +1X6MM2(E)",
      "conduit": "ỐNG PVC D25"
    }
  ],
  "debug": { "scores": { "panel_table": 12 }, "rotation": 0 }
}
```

### `GET /api/results/{job_id}/export.json?confirmed={bool}`
Xuất BOQ toàn dự án dạng **mảng phẳng** các dòng vật tư (gộp mọi trang).
- `confirmed=true`: chỉ lấy trang đã "chốt" (nên dùng cùng bước `confirm-all`).
- `confirmed=false`: lấy mọi trang **đã lưu** (nếu chưa lưu/chốt trang nào → mảng rỗng `[]`).
```json
[
  { "panelName": "TĐTM-1", "roadName": "TĐTM-1", "loadName": "TỦ ĐIỆN SMARTHOME TẦNG 1",
    "itemGroup": "Dây & cáp điện", "itemName": "Dây/cáp Cu/PVC",
    "size": "6mm2", "cableSpec": "CU/PVC 3X(1X6MM2) +1X6MM2 +1X6MM2(E)", "conduit": "ỐNG PVC D25" }
]
```

### `GET /api/results/{job_id}/export.xlsx?confirmed={bool}`
Như trên nhưng trả file Excel (2 sheet: *Chi tiết* + *Tổng hợp*). Header
`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

### `GET /api/results/{job_id}/page/{page}/preview?scale={n}`
Ảnh PNG render của trang (dùng để hiển thị/đối chiếu). `scale` từ `0.2`–`6.0`
(mặc định `1.0`; càng cao càng nét/nặng). Trả `image/png`.

### `GET /api/results/{job_id}/qa?q={câu hỏi}`
Hỏi–đáp rule-based về quan hệ điều khiển/cấp nguồn/tổng công suất đèn. Trả
`{ "answer": "...", "items": [...], "found": true|false }`.

---

## 4. Ý nghĩa các trường trong 1 dòng khối lượng (`items[]` / BOQ)

| Trường | Ý nghĩa | Ví dụ |
|--------|---------|-------|
| `panelName` | Tủ điện / khu vực chứa lộ | `TĐTM-1`, `PUMP ROOM` |
| `roadName` | Tên lộ/mạch (với `mep_tray` = mã hệ thống) | `TĐTM-1`, `LV_TK` |
| `loadName` | Tên tải / tên hệ thống | `TỦ ĐIỆN SMARTHOME TẦNG 1` |
| `itemGroup` | Nhóm vật tư | `Dây & cáp điện`, `Thang máng cáp` |
| `itemName` | Tên vật tư | `Dây/cáp Cu/PVC` |
| `size` | Tiết diện (cáp) hoặc kích thước (máng) | `6mm2`, `200x50` |
| `cableSpec` | Quy cách cáp (với `mep_tray` = cao độ) | `CU/PVC 3X(1X6MM2)...`, `BOT=FFL+2550` |
| `conduit` | Ống luồn (với `mep_tray` = tuyến/ref) | `ỐNG PVC D25` |

**`diagramType`** (loại sơ đồ nhận diện được): `panel_table` (bảng tải), `busbar_slash`
(busbar + vạch chéo), `hotel_db` (tủ DB khách sạn), `mep_tray` (mặt bằng thang–máng cáp),
`unknown` (không bóc được). Mỗi loại đọc được tập trường khác nhau — trường không đọc
được để rỗng `""`.

---

## 5. Lưu ý & giới hạn

- **Cold start:** request đầu sau khi Space ngủ mất 20–60s. Nên đặt timeout ≥ 120s cho
  `/api/analyze` và `confirm-all`, và retry 1 lần nếu gặp `503`.
- **Xử lý đồng bộ:** `/api/analyze` phân tích ngay trong request; PDF nhiều trang/nặng
  sẽ lâu hơn. Đặt timeout đủ lớn.
- **Dữ liệu tạm:** file upload & kết quả lưu tạm trên Space, **mất khi Space restart/build lại**.
  Hãy lấy kết quả về ngay trong phiên; đừng phụ thuộc `job_id` tồn tại lâu dài.
- **Không xác thực:** endpoint mở hoàn toàn — chỉ chia sẻ Base URL trong phạm vi tin cậy.
- **Chỉ nhận PDF vector** (bản vẽ xuất từ CAD). PDF scan ảnh sẽ không bóc được (không có
  text/vector để đọc).

---

## 6. Script kiểm thử API

Có sẵn `scripts/test_api.py` chạy qua toàn bộ endpoint ở trên và báo PASS/FAIL:

```bash
pip install requests
python scripts/test_api.py                       # test Space mặc định + PDF mẫu
python scripts/test_api.py <BASE_URL> <file.pdf> # test server / file khác
API_BASE=http://localhost:8000 python scripts/test_api.py   # test bản chạy local
```

Thoát mã `0` nếu tất cả PASS. Dùng để kiểm tra nhanh sau mỗi lần deploy.

---

## 7. Mã lỗi thường gặp

| HTTP | Ý nghĩa | Cách xử lý |
|------|---------|-----------|
| `400` | File không phải PDF | Gửi đúng file `.pdf` ở field `file` |
| `404` | Sai `job_id`/`page`, hoặc job đã bị xoá (Space restart) | Upload lại từ `/api/analyze` |
| `500` | Lỗi khi phân tích | Kiểm tra PDF có phải bản vẽ vector hợp lệ |
| `503` | Space đang khởi động (cold start) | Chờ vài giây rồi thử lại |

---

## 8. Kết nối qua MCP (dùng trực tiếp trong Claude)

Ngoài REST, Space còn expose một **MCP server** (Model Context Protocol, transport
streamable HTTP) để Claude Desktop / Claude Code / connector trên claude.ai gọi
thẳng các chức năng mà không cần viết code.

- **Endpoint:** `https://tranphuc120203-boc-tach-ban-ve.hf.space/mcp`
- **Xác thực:** không (giống REST — ai có link đều dùng được).
- **Trạng thái:** stateless; `job_id` chỉ sống trong phiên, mất khi Space restart.

### Thêm vào Claude

```bash
# Claude Code
claude mcp add --transport http boc-tach https://tranphuc120203-boc-tach-ban-ve.hf.space/mcp
```

Trên **claude.ai**: Settings → Connectors → *Add custom connector* → dán URL trên.

### Tool có sẵn

| Tool | Công dụng |
|------|-----------|
| `analyze_pdf(pdf_url \| pdf_base64)` | Nạp & phân tích PDF, trả `job_id` + danh sách trang |
| `list_jobs()` | Liệt kê job còn lưu trên server |
| `extract_page(job_id, page, kind="auto")` | Bóc tách khối lượng 1 trang |
| `get_boq(job_id, confirm_all=True)` | BOQ gộp toàn dự án (mảng phẳng) |
| `ask_drawing(job_id, question)` | Hỏi–đáp rule-based về quan hệ trong bản vẽ |
| `normalize_sheet_config(source, strict=True)` | Chuẩn hoá `DocumentSetConfig` JSON/JSONC |
| `validate_sheet_config(config_json)` | Kiểm tra 7 luật của cấu hình |
| `get_sheet_config_template()` | Cấu hình mẫu |

> Cold start vẫn áp dụng: lần gọi đầu sau khi Space ngủ mất 20–60s.
> `analyze_pdf` cần `pdf_url` trỏ tới file `.pdf` tải trực tiếp được, hoặc
> `pdf_base64` (chỉ nên dùng cho file nhỏ).
