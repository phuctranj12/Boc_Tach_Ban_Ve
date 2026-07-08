---
title: Boc Tach Ban Ve MEP
emoji: 📐
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# MEP Drawing Reader — Vector + Graph + (AI sau)

> ℹ️ Khối `---` phía trên là cấu hình bắt buộc cho **Hugging Face Spaces (Docker)**.
> Cách deploy: xem [DEPLOY.md](DEPLOY.md).

Đọc bản vẽ PDF MEP (điện chiếu sáng, ổ cắm, single line, plumbing…) với độ chính xác cao
bằng cách **khai thác vector + layer CAD thật**, dựng **graph topology**, rồi áp **rule engine** —
**không OCR, không AI Vision**. AI/LLM chỉ ghép vào ở bước cuối (Phase 9) khi cần suy luận sâu.

Hiện đã hoàn thành **Phase 1 → 7** + QA rule-based (Phase 10 bản nền) + giao diện React kéo-thả.

---

## Kiến trúc

```
PDF ─▶ PyMuPDF ─▶ Text + Layer + Line ─▶ Object Extractor ─▶ Graph Builder ─▶ Rule Engine ─▶ Knowledge Graph ─▶ (LLM)
```

| Phase | Module | Vai trò |
|------|--------|---------|
| 1 | `core/pdf_parser.py` | Trích words, drawings (làm phẳng polyline), layer CAD |
| 2 | `core/sheet_classifier.py` | Phân loại sheet theo **title block** |
| 3 | `core/object_extractor.py` | Sinh đối tượng chuẩn hoá (switch/light/socket/DB/breaker) |
| 4 | `core/layer_filter.py` | Map layer CAD → nhóm chức năng (wire/light/switch/socket/equipment) |
| 5 | `core/graph_builder.py` | Dựng topology dây bằng NetworkX (snap endpoint + connected components) |
| 6 | `core/rule_engine.py` | Suy luận `controls` / `supplies` / `located_in` (không AI) |
| 7 | `core/pipeline.py` | Cross-sheet linking + tổng hợp kết quả |
| 10 | `core/qa.py` | Hỏi đáp rule-based trên graph |

### Bóc tách khối lượng cáp/ống — package `core/takeoff/` (scale theo nhiều loại bản vẽ)

Mỗi loại sơ đồ nguyên lý là 1 extractor riêng, cùng trả về schema QS giống nhau. Tự nhận diện loại (`detect_type`) qua điểm số.

| File | Loại bản vẽ |
|------|-------------|
| `takeoff/base.py` | Khung chung: `TakeoffItem`/`TakeoffResult`, helper đọc PDF, parse size |
| `takeoff/busbar_slash.py` | **Kiểu A** — busbar + vạch chéo "/" (bọc `core/sld_extractor.py`) |
| `takeoff/panel_table.py` | **Kiểu B** — bảng/ma trận tủ điện (mỗi cột = 1 lộ, neo bởi số mạch) |
| `takeoff/orient.py` | Chuẩn hoá hướng: tự xoay 90/180/270 khi nội dung bị xoay |
| `takeoff/__init__.py` | Registry + auto-detect + auto-orient; thêm kiểu mới chỉ cần thêm 1 module |

➕ Thêm loại bản vẽ mới: tạo `takeoff/<ten>.py` có `detect_score(page)` + `extract(page, idx)`, đăng ký vào `EXTRACTORS`. API/frontend/BOQ không phải sửa.

**Chống xoay (orientation-robust):** đúng hướng → bóc thẳng (nhanh); nếu nội dung bị xoay 90/180/270 thì tự thử các hướng và chọn hướng cho nhiều lộ nhất. Bản vẽ vector CAD không bị nghiêng góc lẻ (tilt) — đó là việc của pipeline scan/OCR, ngoài phạm vi cách vector này.

Mọi ngưỡng heuristic nằm tập trung ở **`app/config.py`** để dễ tinh chỉnh độ chính xác.

---

## Chạy thử

### Backend (Python 3.11+)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
bash backend/run.sh          # http://localhost:8000  (docs: /docs)
```

### Frontend (Node 18+)
```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173  (proxy /api → :8000)
```

Mở trình duyệt → kéo-thả `ban_ve_goc.pdf` vào → xem kết quả.

---

## API chính

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/analyze` | Upload PDF, chạy pipeline, trả kết quả đầy đủ |
| GET | `/api/results/{job_id}` | Lấy lại kết quả |
| GET | `/api/results/{job_id}/qa?q=...` | Hỏi đáp |
| GET | `/api/results/{job_id}/page/{p}/preview?scale=` | Ảnh PNG của trang |
| GET | `/api/results/{job_id}/sld?page={p}&kind=auto` | Bóc tách cáp & ống từ sơ đồ nguyên lý — auto nhận diện Kiểu A/B (JSON QS) |
| GET | `/api/results/{job_id}/review/{p}` | Dữ liệu duyệt 1 trang (bản đã lưu, hoặc bóc tự động) |
| PUT | `/api/results/{job_id}/review/{p}` | Lưu dữ liệu đã sửa + cờ xác nhận cho trang |
| GET | `/api/results/{job_id}/review` | Trạng thái duyệt tất cả trang |
| GET | `/api/results/{job_id}/export.json?confirmed=` | Xuất JSON gộp (QS) |
| GET | `/api/results/{job_id}/export.xlsx?confirmed=` | Xuất Excel BOQ (2 sheet: Chi tiết + Tổng hợp) |

### Human-in-the-loop & xuất BOQ
Trước khi xuất, giao diện chia đôi: **trái** = ảnh bản vẽ trang, **phải** = bảng bóc tách **sửa được** (thêm/xoá/sửa dòng), Lưu & Xác nhận từng trang. Duyệt lần lượt qua các trang rồi **Xuất JSON / Excel** (tuỳ chọn chỉ xuất trang đã xác nhận). Backend: `core/export.py` (openpyxl) + `storage/review_store.py` (lưu chỉnh sửa tách khỏi bản bóc tự động). Frontend: `components/TakeoffReview.jsx`.

---

## Kết quả trên `ban_ve_goc.pdf`

- 14 trang A3 · 859 đối tượng · 68 quan hệ suy luận (34 `controls` + 34 `supplies`)
- Phân loại: 13 `electrical_layout` (Power Supply & Lighting) + 1 `plumbing` (Water Supply)
- QA: *"S1 điều khiển đèn nào?"* → `S1 điều khiển: L1`

---

## Bước tiếp theo (chưa làm)

- **Phase 8 – Neo4j**: hiện dùng NetworkX in-process; có thể đẩy sang Neo4j.
- **Phase 9 – Self-hosted LLM**: ghép graph context vào prompt trong `core/qa.py` (đã chừa chỗ).
- Tinh chỉnh nhận diện symbol bằng hình học (hiện định vị theo nhãn text) để tăng tỉ lệ nối dây.
- Xuất BOQ / Excel / Markdown (Phase 11).

## Cấu trúc thư mục
```
backend/app/
  config.py              # mọi ngưỡng & mapping
  models/                # Pydantic: geometry, objects, sheet, graph
  core/                  # pdf_parser, sheet_classifier, object_extractor,
                         # layer_filter, graph_builder, rule_engine, pipeline, qa
  api/routes.py          # FastAPI endpoints
  storage/store.py       # lưu kết quả JSON + cache
frontend/src/
  api/client.js          # gọi backend
  components/            # FileDropzone, StatsCards, SheetList, RelationshipPanel,
                         # TypeBreakdown, QaBox, PagePreview
  App.jsx
```
