# Logic bóc tách bản vẽ MEP — Tài liệu kỹ thuật

> Mục tiêu của tài liệu: giúp đọc hiểu **toàn bộ cách tool bóc dữ liệu từ PDF ra JSON**,
> đặc biệt là **các thực thể trong bản vẽ liên kết với nhau như thế nào**, mức độ
> **chặt chẽ/tin cậy** của từng liên kết, và **làm sao biết** một liên kết là đúng.
> Viết để dùng lại cho các bài toán bóc tách khác trong tương lai.
>
> Đối chiếu trực tiếp với dữ liệu thật trong [extracted_json/](extracted_json/).
>
> 👉 **Muốn hiểu nhanh bằng ví dụ cụ thể từng bước?** Đọc
> [VI_DU_SUY_LUAN.md](VI_DU_SUY_LUAN.md) trước — nó trace 1 cái đèn/ổ cắm thật từ
> dữ liệu PDF ra JSON. Tài liệu này (LOGIC_BOC_TACH) là bản tham chiếu đầy đủ.

---

## 0. Tóm tắt 1 phút

- Tool **không dùng AI/OCR/Vision**. Mọi thứ là **vector thật** đọc từ PDF bằng PyMuPDF:
  *text có toạ độ* + *nét vẽ (line/rect/curve) có layer*. Đây là gốc rễ của mọi suy luận.
- Có **2 hệ bóc tách song song**, dùng cho 2 mục đích khác nhau:
  - **Hệ A — Knowledge Graph** (`app/core/pipeline.py`): hiểu *quan hệ* giữa thiết bị
    (công tắc điều khiển đèn nào, MCB cấp cho ổ cắm nào…). → `*.analysis.json`.
  - **Hệ B — Takeoff/QS** (`app/core/takeoff/`): bóc *khối lượng* cáp & ống để ra BOQ.
    → `*.takeoff.json`.
- **Liên kết giữa các thực thể** được suy ra theo **hình học** (geometry), không phải
  theo chữ: hai hệ dùng 2 cơ chế liên kết khác nhau (xem [§4](#4-cách-các-thực-thể-liên-kết-với-nhau-phần-quan-trọng-nhất)).
- Mức độ chặt chẽ: **cao** ở chỗ có tín hiệu hình học rõ (vạch chéo, cột thẳng hàng,
  dây nối liền mạch); **trung bình/yếu** ở chỗ phải đoán theo "gần nhất" (nearest-neighbor)
  hoặc theo ngưỡng khoảng cách. Mọi ngưỡng nằm tập trung trong `config.py` / `SLD_CFG` / `CFG`.

---

## 1. Kiến trúc tổng thể

```
            ┌─────────────────────────────────────────────┐
   PDF ──►  │  Phase 1: PDF Parser (PyMuPDF)               │
            │  → words (text+bbox) + drawings (vector+layer)│
            └───────────────┬─────────────────────────────┘
                            │  (dữ liệu thô dùng chung)
          ┌─────────────────┴───────────────────┐
          ▼                                       ▼
  ┌───────────────────────┐          ┌──────────────────────────┐
  │  HỆ A: Knowledge Graph │          │  HỆ B: Takeoff / QS        │
  │  pipeline.py           │          │  takeoff/ (registry)       │
  │  Phase 2→7             │          │  busbar_slash | panel_table│
  │  → analysis.json       │          │  → takeoff.json → BOQ      │
  └───────────────────────┘          └──────────────────────────┘
```

Hai hệ **độc lập**: hệ A trả lời "thiết bị nào nối/điều khiển/ cấp nguồn cho thiết bị nào";
hệ B trả lời "cần bao nhiêu mét cáp loại gì, ống gì". Cả hai cùng đọc 1 nguồn vector.

---

## 2. Phase 1 — Nguồn dữ liệu: vector thật từ PDF

File: [backend/app/core/pdf_parser.py](backend/app/core/pdf_parser.py)

PyMuPDF cho 2 loại dữ liệu, **đều có toạ độ** (đơn vị *point*, A3 ≈ 2384×1684pt):

| Loại | Hàm | Thành quả | Model |
|---|---|---|---|
| Chữ | `page.get_text("words")` | mỗi từ + bbox (x0,y0,x1,y1) | `RawWord` |
| Nét vẽ | `page.get_drawings()` | line/rect/quad/bezier + tên layer | `RawDrawing` |

Mọi nét vẽ được **làm phẳng thành polyline** (`_flatten_items`): rect → 4 cạnh, bezier →
2 đầu mút (đủ cho topology). Curve chỉ giữ 2 đầu vì ta chỉ cần nối mạch, không cần độ cong.

Ví dụ thật (xem [extracted_json/ban_ve_goc.raw_page0.json](extracted_json/ban_ve_goc.raw_page0.json)):

```json
{ "text": "DB-2BR", "x": 700.1, "y": 260.6 }        // 1 từ, có tâm
{ "layer": "E-Line", "group": "wire",
  "pts": [[318.0, 1006.2], [1067.4, 1006.2]] }        // 1 đoạn dây ngang
```

> **Điểm mấu chốt:** vì có toạ độ chính xác tới point, ta liên kết thực thể bằng
> **vị trí tương đối** (gần/thẳng hàng/cắt nhau) thay vì đoán bằng ngữ nghĩa chữ.
> Đây là lý do kết quả *tất định* (chạy lại luôn ra y hệt) và *giải thích được*.

---

## 3. Hệ A — Knowledge Graph (analysis.json)

Orchestrator: [backend/app/core/pipeline.py](backend/app/core/pipeline.py). Chạy lần lượt:

### Phase 2 — Phân loại trang `sheet_classifier.py`
Đọc **tiêu đề trong title block** (góc dưới-phải, `TITLE_BLOCK_REGION = (0.6,0.6,1,1)`),
so với `SHEET_KEYWORDS`. Title block quyết định, full-text chỉ dùng khi title trống —
vì legend/ký hiệu lặp trên mọi trang sẽ gây nhiễu. Kết quả: `electrical_layout`,
`plumbing`, `single_line`, `panel_schedule`…

### Phase 3 — Trích đối tượng `object_extractor.py`
Mỗi từ khớp một regex trong `LABEL_PATTERNS` → 1 `MEPObject` đặt tại **tâm bbox**:

| type | regex | ví dụ |
|---|---|---|
| distribution_board | `^(DB\|MDB\|SDB)[-/].+` | DB-2BR |
| breaker | `^\d+P-\d+A$`, `^MCB$` | 2P-63A, MCB |
| switch | `^S\d+[A-Za-z]?$` | S1, S2a |
| light | `^L\d+[A-Za-z]?$` | L1 |
| socket | `^P\d+[A-Za-z]?$` | P5 |

Suy thêm thuộc tính: đèn lấy công suất "9W" gần nhất (≤35pt); breaker tách `poles`/`rating`.
Phòng (`room`) nhận theo từ điển tiếng Việt (BẾP, NGỦ, WC…) cho quan hệ không gian.

### Phase 4 — Phân loại layer `layer_filter.py`
Tên layer trong PDF bị lồng xobject: `"4821 - UNIT LAYOUT...$0$A-WALL"`. Lấy phần sau
`$0$`/`|` rồi map về nhóm bằng `LAYER_GROUPS`: **wire / light / switch / socket /
equipment / text**. `wire` xét trước `socket` (vì "E-PO WIRING" vs "E-PO").

### Phase 5 — Xây topology `graph_builder.py` ⭐
**Đây là trái tim của việc liên kết.** Xem chi tiết [§4.1](#41-hệ-a--liên-kết-bằng-mạng-dây-điện-vector).

### Phase 6 — Suy luận quan hệ ngữ nghĩa `rule_engine.py`
Từ `connected_to` suy ra quan hệ có nghĩa (xem [§4.2](#42-hệ-a--từ-nối-mạch-suy-ra-điều-khiển--cấp-nguồn)).

### Phase 7 — Liên kết xuyên trang `pipeline._cross_sheet_links`
Cùng `(label, type)` xuất hiện ở ≥2 trang → nối `cross_ref` (vd `S2` trang 0 ↔ `S2`
trang 1). **Yếu nhất** vì chỉ dựa trên trùng tên, không kiểm chứng hình học.

Thống kê thật trên `ban_ve_goc` (14 trang) — xem `stats` trong analysis.json:
```
nodes 859 | connected_to 166 | controls 34 | supplies 49 | located_in 845 | cross_ref 268
by_type: breaker 356, distribution_board 190, socket 149, switch 118, light 46
```

---

## 4. Cách các thực thể liên kết với nhau (PHẦN QUAN TRỌNG NHẤT)

Có **3 cơ chế liên kết** khác nhau, độ tin cậy giảm dần:

| Cơ chế | Dùng ở | Bằng chứng hình học | Độ chặt chẽ |
|---|---|---|---|
| **Nối theo nét dây** | Hệ A, Phase 5–6 | dây vector nối liền 2 thiết bị | ★★★ cao (nếu dây liền) |
| **Thẳng hàng / vạch chéo** | Hệ B (takeoff) | cột thẳng trục x, vạch "/" tại giao điểm | ★★★ cao |
| **Gần nhất theo khoảng cách** | located_in, terminal, chuỗi | "ai gần thì gắn" + ngưỡng | ★★ trung bình |
| **Trùng nhãn** | cross_ref | cùng chuỗi text trên nhiều trang | ★ thấp |

### 4.1 Hệ A — Liên kết bằng **mạng dây điện vector**

File: [backend/app/core/graph_builder.py](backend/app/core/graph_builder.py). 5 bước:

1. **Lấy nét dây**: chỉ các `drawing.group == "wire"`.
2. **Snap đầu dây về lưới**: toạ độ chia cho `WIRE_SNAP_TOLERANCE=3.0` rồi làm tròn →
   2 đầu dây cách nhau <3pt coi là **cùng một nút mạng**. (Bỏ đoạn <`MIN_WIRE_LENGTH=1`.)
3. **Nối nút bằng NetworkX**: mỗi đoạn dây = 1 cạnh. → các **thành phần liên thông**
   (connected components) = các "mạng dây rời nhau".
4. **Gắn thiết bị vào dây**: mỗi `MEPObject` tìm nút mạng dây gần nhất trong
   `OBJECT_ATTACH_TOLERANCE=55.0`pt. Xa hơn → coi như **không nối** (bỏ).
5. **Cùng 1 mạng = liên thông**: các thiết bị rơi vào cùng một component được nối
   thành **chuỗi hàng xóm gần nhất** (nearest-neighbor path), tạo cạnh `connected_to`.

```
   S1 ●───────────● L1        →  cùng 1 component dây
        (nét wire)               →  connected_to: S1–L1  (weight = khoảng cách)
```

Ví dụ thật (ban_ve_goc.analysis.json):
```json
{ "source": "p0.2P-63A", "target": "p0.MCB", "relation": "connected_to", "weight": 72.8 }
```

**Chặt chẽ tới đâu?**
- ✅ *Mạnh* khi dây vẽ liền nét và thiết bị đặt sát dây. Bằng chứng là **vật lý** (có
  đường dây thật trên bản vẽ).
- ⚠️ *Điểm gãy*: (a) nếu dây bị **đứt đoạn** > 3pt mà không cùng snap → mạng bị chia
  đôi, mất liên kết; (b) nếu 2 mạng khác nhau chạy sát nhau < 55pt → thiết bị có thể
  bị gắn nhầm mạng; (c) **chuỗi nearest-neighbor** chỉ là *một* cách nối các thiết bị
  trong cùng mạng — nó **không** tái tạo đúng cấu trúc rẽ nhánh (T-junction). Với mạch
  hình sao (1 nguồn → nhiều tải) thì chuỗi tuyến tính là *xấp xỉ*, không phải sơ đồ thật.

### 4.2 Hệ A — Từ "nối mạch" suy ra "điều khiển / cấp nguồn"

File: [backend/app/core/rule_engine.py](backend/app/core/rule_engine.py). Trong **mỗi
component liên thông** (`connected_to`):

- **Rule 1**: có `switch` + có `light` → switch **controls** mọi light trong mạng đó.
- **Rule 2/3**: có `breaker`/`distribution_board` + có `socket`/`equipment` →
  feeder **supplies** các tải đó.
- **Rule 4** (không gian, không qua dây): mỗi thiết bị gắn `located_in` phòng gần nhất
  ≤ `350`pt.

Ví dụ thật:
```json
{ "rule": "Rule1",   "subject": "S1",     "relation": "controls", "objects": ["L1"] }
{ "rule": "Rule2/3", "subject": "2P-10A", "relation": "supplies", "objects": ["P6"] }
```

**Chặt chẽ tới đâu?**
- ✅ Logic suy luận đúng *nếu* topology Phase 5 đúng.
- ⚠️ Rule 1/2/3 nối **tất-cả-với-tất-cả** trong 1 component: nếu 1 mạng gộp nhầm 3 công
  tắc + 1 đèn, nó sẽ nói *cả 3* công tắc điều khiển đèn đó (thấy rõ trong dữ liệu:
  S1, S2, S3 cùng "controls L1"). Đúng với mạch đảo chiều (2-way), nhưng cũng có thể là
  *gộp mạng sai*. Đây là chỗ cần con người duyệt lại.
- ⚠️ `located_in` chỉ là "gần nhãn phòng nhất" → với phòng lớn/nhãn đặt lệch sẽ sai.
  (845 cạnh located_in cho thấy nó gắn rất "hào phóng".)

### 4.3 Hệ B — Liên kết bằng **thẳng hàng & vạch chéo** (chính xác hơn cho QS)

Hệ B không dựa vào việc dò mạng dây liền mạch (sơ đồ nguyên lý thường vẽ tượng trưng),
mà dựa vào **quy ước trình bày bản vẽ**. Có 2 kiểu:

#### Kiểu A — `busbar_slash` (file ban_ve_goc)
File: [backend/app/core/sld_extractor.py](backend/app/core/sld_extractor.py).

```
            L1   S1   P1  ...        ← hàng TERMINAL (đầu lộ)
            │    │    │
  cáp #1 ───┼────/────┼──────         ← đường cáp ngang (mỗi loại cáp 1 mức y)
  cáp #2 ───/─────────┼──────              "/" = VẠCH CHÉO tại giao điểm
            │    │    │
          [tải][tải][tải]            ← cột mô tả tải (text dọc)
```

Quy tắc liên kết (đều là hình học):
1. **Cáp ↔ spec**: mỗi đường ngang khớp cột text "2x1C…" theo `x_start` (≤ `spec_match_x_tol×3`).
2. **Tải ↔ cáp**: tại cột của tải, tìm **vạch chéo "/"** (đoạn dài 5–16pt, nghiêng 25–65°)
   gần nhất theo x (≤ `slash_match_x_tol=16`). Vạch chéo nằm trên đường cáp nào → **đó là
   cáp của tải đó**. Đây là tín hiệu **rất chắc** vì người vẽ cố ý đánh dấu.
3. **Tải ↔ terminal (roadName)**: terminal gần nhất theo x (≤ `load_terminal_x_tol=60`).

Ví dụ thật (ban_ve_goc.takeoff.json, page 0):
```json
{ "panelName": "DB-2BR", "roadName": "L1", "loadName": "QUẠT HÚT TOILET",
  "size": "2.5mm2", "cableSpec": "2x1C 2.5mm2 Cu/PVC + 1C-2.5mm2 Cu/PVC (E)",
  "conduit": "ỐNG PVC D20/ PVC D20" }
```
debug: `n_routes:4, n_slashes:12, n_terminals:11, n_loads:13` → 13 tải, mỗi tải bắt đúng
1 trong 4 loại cáp nhờ vạch chéo.

**Chặt chẽ:** ★★★ — vạch chéo là **bằng chứng do người vẽ chủ động đặt**, không phải suy đoán.
Điểm gãy: nếu bản vẽ không có vạch chéo, hoặc vạch chéo lệch cột > 16pt thì tải mất cáp.

#### Kiểu B — `panel_table` (file loại 2)
File: [backend/app/core/takeoff/panel_table.py](backend/app/core/takeoff/panel_table.py).

```
   power→ 6000   3000          ← text ngang (công suất, CB) phía trên
   CB →   MCB.. MCB..
          ┌───┐ ┌───┐
  cáp  →  │CU/││CU/│           ← text DỌC trong cột
  ống  →  │PVC││PVC│
  tải  →  │Ổ..││Ổ..│
          └───┘ └───┘
   ref →   S1    S2            ← SỐ MẠCH neo cột (hàng ngang dưới)
```

Quy tắc liên kết: **số mạch (S1, FCU 1, SS1.1…) là cái neo cột**. Mọi text DỌC có
`|x − ref.x| ≤ col_x_tol(9)` và nằm **phía trên** ref trong `col_y_up(160)`pt thuộc về
cột đó → phân loại theo nội dung: có "MM2" & không "ỐNG" = **cáp**; có "ỐNG" = **ống
luồn**; còn lại = **tên tải**. Text NGANG phía trên (lệch phải tối đa 14pt) = **công
suất** (số thuần) + **CB** (MCB/RCBO/…).

Ví dụ thật (loai_2.takeoff.json):
```json
{ "panelName": "TĐTM-1", "roadName": "TĐTM-1", "loadName": "TỦ ĐIỆN SMARTHOME TẦNG 1",
  "power": "6000", "cb": "MCB 3P 32A 6kA", "size": "6mm2",
  "cableSpec": "CU/PVC 3X(1X6MM2) +1X6MM2 +1X6MM2(E)", "conduit": "ỐNG PVC D25" }
```
Ngoài lộ thường, tủ con (`TĐTM-x`) cũng là 1 cột → thêm 1 dòng **feeder** (vì tủ con
cũng cần dây). Tủ tổng (`TĐ-Tx`) gom riêng vào `panels` kèm P/Ptt/Kđt:
```json
{ "name": "TĐ-T1", "kind": "main", "power": "64000", "ptt": "38400", "kdt": "0.60" }
```

**Chặt chẽ:** ★★★ cho liên kết *trong cột* (thẳng trục x là quy ước bảng rất mạnh).
Điểm gãy: gán **tên tủ cho cụm cột** (`_assign_panels_by_cluster`) dựa vào "nhãn tủ gần
mép trái cụm nhất" — đây là heuristic ★★, dễ sai nếu bố cục nhiều tủ chen nhau.

### 4.4 Làm sao **biết** một liên kết là đúng?

1. **Đọc `debug`** trong takeoff.json: `n_routes / n_slashes / n_terminals / n_loads`
   (Kiểu A) hay `n_refs / clusters` (Kiểu B). Số tải ≈ số vạch chéo / số cột là dấu hiệu
   khớp tốt; lệch nhiều = nghi ngờ.
2. **`weight`** trên cạnh `connected_to`/`located_in` = khoảng cách (point). Weight nhỏ
   → liên kết tin cậy; weight sát ngưỡng (≈55 cho attach, ≈350 cho room) → đáng ngờ.
3. **`detect.scores`**: điểm tự nhận loại sơ đồ. Nếu điểm thấp/đều nhau → có thể nhận
   nhầm loại.
4. **Xem lại nguồn** trong `raw_page0.json`: đối chiếu toạ độ của 2 thực thể nghi vấn
   xem chúng có thật sự thẳng hàng / có dây nối không.
5. **Human-in-the-loop**: UI duyệt theo trang (xem [§6](#6-duyệt-sửa--xuất-boq)) chính
   là để con người xác nhận các liên kết ★★/★ trước khi xuất BOQ.

---

## 5. Schema JSON đầu ra

### 5.1 `analysis.json` (Hệ A)
```jsonc
{
  "job_id", "filename", "page_count",
  "sheets": [ { "page","sheet_no","sheet_type","title","object_counts",... } ],
  "nodes": [ { "id":"p0.S1","label":"S1","type":"switch","page":0,"x","y","attrs":{} } ],
  "edges": [ { "source","target","relation","page","weight","attrs" } ],
  //   relation ∈ connected_to | controls | supplies | located_in | cross_ref
  "relationships": [ { "rule","subject","relation","objects":[...],"detail" } ],
  "stats": { "nodes","connected_to","supplies","by_type",... }
}
```

### 5.2 `takeoff.json` (Hệ B) — 1 phần tử / trang
```jsonc
{
  "page", "diagramType",          // busbar_slash | panel_table | unknown
  "panelName",
  "panels": [ { "name","kind","power","ptt","kdt" } ],   // tủ tổng/tủ con
  "items": [ {                    // mỗi item = 1 dòng BOQ
     "panelName","roadName","loadName","power","cb",
     "itemGroup":"Dây & cáp điện","itemName":"Dây/cáp Cu/PVC",
     "size","cableSpec","conduit"
  } ],
  "debug": { "scores","rotation","n_routes",... }
}
```
Schema `items` **giống nhau** cho mọi loại sơ đồ → API/Excel không cần biết loại bản vẽ.

---

## 6. Duyệt, sửa & xuất BOQ

File: [backend/app/api/routes.py](backend/app/api/routes.py), `storage/review_store.py`,
`core/export.py`.

- Sau khi upload, server **bóc trước tất cả trang** ở chế độ nền (`_prewarm_extract`),
  cache 2 tầng (RAM + đĩa) để duyệt không phải chờ.
- `GET /review/{page}` trả bản đã sửa nếu có, ngược lại bóc tự động.
- `PUT /review/{page}` lưu chỉnh sửa + cờ `confirmed`.
- `confirm-all` rồi `export.xlsx` / `export.json` (lọc `confirmed` nếu muốn).

→ Đây là tầng "chốt" cho mọi liên kết độ tin cậy ★★/★: con người sửa, rồi mới xuất.

---

## 7. Các ngưỡng (threshold) — chỉnh ở đâu

| Ngưỡng | File | Ý nghĩa | Tăng lên → | Giảm xuống → |
|---|---|---|---|---|
| `WIRE_SNAP_TOLERANCE` 3.0 | config.py | gộp đầu dây thành nút | nối "rộng tay" hơn (dễ gộp nhầm) | dễ đứt mạng |
| `OBJECT_ATTACH_TOLERANCE` 55 | config.py | thiết bị→dây | bắt thêm thiết bị xa | bỏ sót thiết bị |
| `slash_match_x_tol` 16 | SLD_CFG | tải↔vạch chéo | dễ bắt nhầm cáp | tải dễ mất cáp |
| `col_x_tol` 9 | panel_table CFG | text↔cột | gộp nhầm cột bên cạnh | rớt text khỏi cột |
| `load_terminal_x_tol` 60 | SLD_CFG | tải↔terminal | gán nhầm terminal | tải thiếu roadName |

**Nguyên tắc:** mọi con số "ma thuật" đều nằm trong 3 chỗ này (`config.py`, `SLD_CFG`,
`panel_table.CFG`) — tinh chỉnh độ chính xác **không cần đụng logic**.

---

## 8. Đánh giá độ chặt chẽ & gợi ý tương lai

**Mặt mạnh**
- Tất định, giải thích được, không phụ thuộc model/AI → dễ kiểm toán.
- Liên kết bằng *bằng chứng hình học do người vẽ đặt* (vạch chéo, cột thẳng hàng) rất chắc.
- Kiến trúc registry (`takeoff/`) cho phép thêm loại sơ đồ mới = thêm 1 module
  (`detect_score` + `extract`), không sửa API/Excel/frontend.

**Mặt yếu / rủi ro (cần con người duyệt)**
1. **Chuỗi nearest-neighbor** (Phase 5) không tái tạo đúng cây rẽ nhánh → quan hệ
   controls/supplies có thể nối thừa trong 1 component.
2. **Gộp/đứt mạng dây** nhạy với `snap`/`attach tolerance`.
3. **cross_ref** chỉ theo trùng tên → có thể nối nhầm 2 thiết bị cùng tên khác mạch.
4. **Gán tủ theo cụm cột** (panel_table) là heuristic vị trí, dễ sai khi bố cục lạ.
5. Phụ thuộc **PDF có vector thật**: bản scan ảnh sẽ không bóc được (cần OCR — ngoài phạm vi).

**Gợi ý mở rộng**
- Thay chuỗi nearest-neighbor bằng **cây Steiner/MST trên mạng dây** + nhận diện node rẽ
  để tái tạo đúng phân nhánh.
- Thêm **điểm tin cậy (confidence)** cho mỗi item dựa trên weight/khoảng cách ngưỡng, để
  UI tô đỏ những liên kết đáng ngờ trước.
- Tận dụng `qa.py` làm chỗ ghép context graph → LLM self-hosted cho hỏi-đáp tự nhiên
  (đã chừa sẵn chỗ ở Phase 9/10).

---

## 9. Bản đồ file nguồn (đọc theo thứ tự)

| Thứ tự đọc | File | Vai trò |
|---|---|---|
| 1 | [pdf_parser.py](backend/app/core/pdf_parser.py) | Nguồn vector (words + drawings) |
| 2 | [models/](backend/app/models/) | Kiểu dữ liệu: Point/BBox, MEPObject, Sheet, Graph |
| 3 | [object_extractor.py](backend/app/core/object_extractor.py) | Text → MEPObject |
| 4 | [graph_builder.py](backend/app/core/graph_builder.py) | ⭐ Mạng dây → connected_to |
| 5 | [rule_engine.py](backend/app/core/rule_engine.py) | connected_to → controls/supplies |
| 6 | [pipeline.py](backend/app/core/pipeline.py) | Ghép Phase 1–7 → analysis.json |
| 7 | [sld_extractor.py](backend/app/core/sld_extractor.py) | ⭐ Kiểu A: busbar + vạch chéo |
| 8 | [takeoff/panel_table.py](backend/app/core/takeoff/panel_table.py) | ⭐ Kiểu B: bảng cột |
| 9 | [takeoff/__init__.py](backend/app/core/takeoff/__init__.py) | Registry + auto-detect + chống xoay |
| 10 | [api/routes.py](backend/app/api/routes.py) | API, cache, duyệt, export |
| 11 | [config.py](backend/app/config.py) | Mọi ngưỡng heuristic |
