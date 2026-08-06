# Sheet Configure API — đặc tả tích hợp

Chuẩn hoá cấu hình bộ bản vẽ shop (`DocumentSetConfig`): nhận JSON/JSONC viết
tay tuỳ tiện, trả về JSON hợp lệ kèm chẩn đoán.

Tài liệu này viết đủ chi tiết để **tích hợp mà không cần thử sai**: mọi trường,
mọi giá trị mặc định, mọi thông báo lỗi và mọi đảm bảo về định dạng đầu ra đều
được liệt kê tường minh, kèm bài kiểm tra tự đối chiếu ở mục 12.

> **Không liên quan tới API bóc tách bản vẽ.** Hai luồng chỉ dùng chung một chỗ
> deploy, không dùng chung dữ liệu. API bóc tách xem [API_DOCS.md](API_DOCS.md).

---

## 0. Tóm tắt máy đọc

```yaml
service:        sheet-configure
version:        "0.1.0"
base_url:       https://tranphuc120203-boc-tach-ban-ve.hf.space
prefix:         /api/sheet-config
auth:           none
cors:           "*"
stateless:      true          # không lưu gì, không session, không job id
deterministic:  true          # cùng input luôn cho cùng output
idempotent:     true          # normalize(normalize(x)) == normalize(x)
retry_safe:     true          # không có tác dụng phụ
max_body_bytes: 2097152       # 2 MB
charset:        utf-8
openapi:        /openapi.json
swagger_ui:     /docs
human_ui:       /json-to-sheet

endpoints:
  - {method: GET,  path: /api/sheet-config/health,    body: none}
  - {method: GET,  path: /api/sheet-config/template,  body: none}
  - {method: POST, path: /api/sheet-config/normalize, body: "JSONC thô hoặc {source}"}
  - {method: POST, path: /api/sheet-config/validate,  body: "JSON config"}

status_codes:
  200: hợp lệ
  400: không parse được, hoặc top-level không phải object   # lỗi dữ liệu, đừng retry
  413: body vượt 2 MB                                        # lỗi dữ liệu, đừng retry
  422: parse được nhưng vi phạm luật                         # lỗi dữ liệu, đừng retry
  503: thiếu Node runtime phía server                        # lỗi hạ tầng, retry được
```

Lệnh gọi tối thiểu:

```bash
curl -X POST --data-binary @DocumentSetConfig.jsonc \
  -H 'Content-Type: text/plain' \
  'https://tranphuc120203-boc-tach-ban-ve.hf.space/api/sheet-config/normalize?strict=1'
```

---

## 1. Vấn đề được giải quyết

File cấu hình gốc viết tay nên là **JSONC**, không phải JSON: có `//`, `/* */`,
và dấu phẩy thừa trước `}` `]`. `System.Text.Json` (C#), `json` (Python),
`Jackson` (Java) đều ném exception.

Đường đi của dữ liệu, đúng thứ tự này:

```
JSONC thô
   │ 1. cleanJsonc     — bỏ chú thích + dấu phẩy thừa
   ▼
JSON text
   │ 2. JSON.parse     — hỏng ở đây -> 400
   ▼
object thô
   │ 3. normalizeConfig — bù mặc định, ép kiểu, giữ trường lạ
   │ 4. collectWarnings — ghi nhận chỗ đã bù
   │ 5. validateConfig  — 7 luật; có lỗi -> 422
   ▼
JSON hợp lệ (trường `json`)
```

---

## 2. Chọn endpoint

| Bạn cần | Endpoint |
|---|---|
| Đọc file `.jsonc` của người dùng, xuất `.json` sạch | `POST /normalize` |
| Kiểm tra cấu hình có sẵn còn hợp lệ không | `POST /validate` |
| Lấy cấu hình mặc định để dựng form | `GET /template` |
| Kiểm tra dịch vụ sống / đánh thức Space | `GET /health` |

Hầu hết tích hợp chỉ dùng `POST /normalize`.

---

## 3. `POST /normalize`

### 3.1 Request

| Cách gửi | `Content-Type` | Body |
|---|---|---|
| **Thô** (khuyến nghị) | `text/plain` | Nguyên văn file, không escape |
| Bọc | `application/json` | `{"source": "<nội dung file>"}` |

Quy tắc chọn: chỉ khi `Content-Type` chứa `application/json` **và** body parse
được thành object có trường `source` kiểu string thì mới lấy `source`. Mọi
trường hợp khác đều coi cả body là nội dung cần xử lý.

| Query | Kiểu | Mặc định | Tác dụng |
|---|---|---|---|
| `strict` | `"1"` | tắt | Gộp toàn bộ `warnings` vào `issues` → `422` thay vì `200` |
| `pretty` | `"0"` | bật | `json` xuất một dòng thay vì thụt lề 2 khoảng trắng |

### 3.2 Response — JSON Schema

```json
{
  "type": "object",
  "required": ["ok", "config", "json", "issues", "warnings", "stats"],
  "properties": {
    "ok":       {"type": "boolean", "description": "true khi issues rỗng"},
    "config":   {"type": "object",  "description": "cấu hình đã chuẩn hoá"},
    "json":     {"type": "string",  "description": "chuỗi để ghi thẳng ra file"},
    "issues":   {"type": "array", "items": {"type": "string"}},
    "warnings": {"type": "array", "items": {"type": "string"}},
    "stats": {
      "type": "object",
      "required": ["packages", "totalSheets", "requiredSheets", "cadSheets"],
      "properties": {
        "packages":       {"type": "integer"},
        "totalSheets":    {"type": "integer"},
        "requiredSheets": {"type": "integer"},
        "cadSheets":      {"type": "integer"}
      }
    }
  }
}
```

Response `400`/`503` có dạng khác:

```json
{"type": "object", "required": ["ok", "error"],
 "properties": {"ok": {"const": false}, "error": {"type": "string"}}}
```

`422` trả về **đầy đủ schema thành công** (có `config`, `json`) kèm `issues`
không rỗng — để người dùng nhìn thấy dữ liệu đã chuẩn hoá mà sửa.

### 3.3 Quy tắc bắt buộc khi dùng kết quả

> **Ghi thẳng chuỗi `json`. Không serialize lại từ `config`.**

`stats` được tính là: `totalSheets` = tổng `Count` mọi sheet; `requiredSheets` =
tổng `Count` các sheet có `IsRequired = true`; `cadSheets` = tổng `Count` các
sheet có `SourceType` bằng `"cad"` khi so sánh không phân biệt hoa thường.

---

## 4. Đảm bảo về định dạng đầu ra

Những điều sau **đã được kiểm chứng bằng test**, có thể dựa vào khi tích hợp:

| Đảm bảo | Chi tiết |
|---|---|
| Thụt lề | 2 khoảng trắng (trừ khi `pretty=0`) |
| Encoding | UTF-8, **không** escape phi-ASCII. `"Căn hộ"` giữ nguyên, không thành `ă` |
| Số nguyên | In không có phần thập phân: `51.0` → `51` |
| Số thực | Giữ nguyên: `1.2` → `1.2`, `0.05` → `0.05` |
| Thứ tự khoá | 8 khoá chuẩn đúng thứ tự `TitleBlock, Keyplan, Grid, Viewport, DualView, ViewSplitter, Workset, PackageTypes`, rồi mới tới các khoá lạ theo thứ tự xuất hiện trong input |
| Trường lạ | Giữ nguyên ở mọi cấp — bạn có thể nhét metadata riêng vào |
| Idempotent | Đưa `json` quay lại `normalize` cho ra đúng chuỗi cũ, và `warnings` rỗng |
| Xác định | Cùng input luôn cho cùng output byte-for-byte |

Đây là lý do phải dùng `json` thay vì serialize lại: thư viện JSON của Python in
`51.0` chứ không phải `51`, và không giữ được các đảm bảo trên.

---

## 5. Lược đồ cấu hình đầy đủ

Mọi trường đều **tuỳ chọn**. Thiếu thì bù giá trị ở cột "Mặc định" và ghi một
dòng vào `warnings`.

### `TitleBlock`

| Trường | Kiểu | Mặc định |
|---|---|---|
| `TitleBlockWidthMm` | number | `51` |
| `SheetMarginLeftMm` | number | `12` |
| `SheetMarginRightMm` | number | `6` |
| `SheetMarginTopMm` | number | `6` |
| `SheetMarginBottomMm` | number | `6` |

### `Keyplan`

| Trường | Kiểu | Mặc định |
|---|---|---|
| `Anchor` | `"TopLeft"` \| `"TopRight"` \| `"BottomLeft"` \| `"BottomRight"` | `"BottomRight"` |
| `OffsetXMm` | number | `0` |
| `OffsetYMm` | number | `5` |
| `CanvasWidthMm` | number | `60` |
| `CanvasHeightMm` | number | `40` |
| `LabelFontSizeMm` | number | `2` |
| `UseViewplanKeyplan` | bool | `true` |
| `SuppressViewportTitle` | bool | `true` |
| `HighlightLineWeight` | number | `7` |
| `HatchSpacingMm` | number | `1.2` |
| `HighlightColorHex` | string, 6 ký tự HEX | `"FF0000"` |
| `HighlightLineStyleName` | string | `"KP_Highlight"` |
| `NormalLineStyleName` | string | `"<Medium Lines>"` |
| `ViewTemplateName` | string | `"HW_KEYPLAN"` |
| `ForceRecreate` | bool | `true` |

### `Grid`

| Trường | Kiểu | Mặc định |
|---|---|---|
| `EnableGridTrim` | bool | `true` |
| `BubbleExtensionMm` | number | `100` |
| `ShowBubbleTop` | bool | `false` |
| **`ShowBubbleBotton`** | bool | `false` |
| `ShowBubbleRight` | bool | `true` |
| `ShowBubbleLeft` | bool | `true` |

> ⚠️ `ShowBubbleBotton` **viết thiếu chữ "m"** — đây là lỗi chính tả có thật
> trong schema gốc, không phải lỗi tài liệu. Gửi `ShowBubbleBottom` sẽ bị coi
> là trường lạ: nó được giữ nguyên trong output nhưng **không có tác dụng**, và
> `ShowBubbleBotton` vẫn nhận giá trị mặc định `false`.

### `Viewport`

| Trường | Kiểu | Mặc định |
|---|---|---|
| `MinClearanceMm` | number | `10` |
| `AutoRotateAspectRatio` | number | `1.5` |

### `DualView`

| Trường | Kiểu | Mặc định |
|---|---|---|
| `Enabled` | bool | `true` |
| `ViewGapMm` | number ≥ 0 | `50` |
| `PreferHorizontal` | bool | `true` |

### `ViewSplitter`

| Trường | Kiểu | Mặc định |
|---|---|---|
| `ExtentPaddingXMm` | number | `10` |
| `ExtentPaddingYMm` | number | `10` |
| `ScaleMin` | number | `50` |
| `ScaleMax` | number | `75` |
| `MinFillRatio` | number | `0.05` |
| `ScaleStep` | number | `5` |
| `MinTilePaperMm` | number | `60` |
| `UseEnhancedLogic` | bool | `true` |

### `Workset`

| Trường | Kiểu | Mặc định |
|---|---|---|
| `Name` | string | `"91.LINK CAD"` |

### `PackageTypes[]`

| Trường | Kiểu | Mặc định khi thiếu |
|---|---|---|
| `Key` | string | `"Package<i>"` với `i` bắt đầu từ 1 |
| `DisplayName` | string | `"Bộ bản vẽ <i>"` |
| `ModelGroupPatterns` | string[] | `[]` |
| `Sheets` | object[] | `[]` |

`ModelGroupPatterns` lọc nhóm model theo tên, `*` nghĩa là tất cả, `APT-*` nghĩa
là các nhóm bắt đầu bằng `APT-`.

Nếu **cả mảng `PackageTypes` thiếu hoặc không phải mảng**, server thay bằng
**3 bộ bản vẽ mẫu của template** — xem cảnh báo ở mục 7.

### `PackageTypes[].Sheets[]`

| Trường | Kiểu | Mặc định khi thiếu |
|---|---|---|
| `DrawingType` | string | `"NewDrawing"` |
| `SourceType` | string | `"Blank"` |
| `DisplayName` | string | `"Bản vẽ mới"` |
| `Count` | number ≥ 1 | `1` |
| `IsRequired` | bool | `true` |

Giá trị `DrawingType` mà giao diện web liệt kê sẵn:

```
ToBia  ToLot  DanhMucBanVe  Legend  MatBangCombine  MatBangThiCong
SoDoNguyenLy  ChiTietLapDat  ChiTietMatCat  Blank
```

Mười giá trị này khớp 1-1 với các loại bản vẽ của add-in Revit:

| Key add-in | `DrawingType` |
|---|---|
| `DrwTp_CoverPage` | `ToBia` |
| `DrwTp_LiningPage` | `ToLot` |
| `DrwTp_DrawingList` | `DanhMucBanVe` |
| `DrwTp_Legend` | `Legend` |
| `DrwTp_SchematicDiagram` | `SoDoNguyenLy` |
| `DrwTp_LayoutPlan` | `MatBangThiCong` |
| `DrwTp_LayoutPlanCombine` | `MatBangCombine` |
| `DrwTp_SectionDetail` | `ChiTietMatCat` |
| `DrwTp_InstallationDetail` | `ChiTietLapDat` |
| `DrwTp_Blank` | `Blank` |

Giá trị `SourceType`: `Cover`, `Index`, `Cad`, `Blank`.

> `Blank` xuất hiện ở cả hai danh sách nhưng là **hai trường khác nhau**:
> `DrawingType = "Blank"` là tờ trắng, còn `SourceType = "Blank"` là nguồn nội dung rỗng.

> Hai danh sách trên **không bị ép buộc** — API chấp nhận chuỗi bất kỳ. Chúng chỉ
> là các lựa chọn dựng sẵn. Nhưng chỉ `SourceType = "Cad"` mới kích hoạt luật
> bắt buộc phải có `Workset.Name`.

---

## 6. Quy tắc ép kiểu

`normalizeConfig` áp dụng ngữ nghĩa của JavaScript. Điều này quan trọng khi
input có kiểu sai:

| Trường | Phép ép | Hệ quả cần biết |
|---|---|---|
| `DrawingType`, `SourceType`, `DisplayName` của sheet | `String(v)` | `123` → `"123"`; `null` → dùng mặc định |
| `Count` | `Number(v)` | `"3"` → `3`. `"abc"` → `NaN` — xem cảnh báo bên dưới |
| `IsRequired` | `Boolean(v)` | `0`, `""` → `false`; `"false"` → **`true`** (chuỗi không rỗng) |
| `ModelGroupPatterns` | `Array.map(String)` | Chỉ nhận khi đã là mảng, ngược lại thành `[]` |
| `Key`, `DisplayName` của bộ | giữ nếu là string | Kiểu khác → dùng mặc định, ghi warning |

Chỉ trường thiếu (`undefined`) hoặc `null` mới rơi về mặc định. Ba nhóm scalar
được merge nông: `{...mặc_định, ...input}` từng nhóm một.

### ⚠️ `Count` không phải số sẽ lọt qua kiểm tra và ra `null`

Đây là lỗ hổng duy nhất trong tầng kiểm tra, cần chặn ở phía client:

```jsonc
// gửi lên
{"Workset": {"Name": "K"},
 "PackageTypes": [{"Key": "A", "Sheets": [{"Count": "abc"}]}]}

// nhận về: 200 OK, issues rỗng, ok = true
{"Count": null}          // trong trường `json`
```

`Number("abc")` cho `NaN`, mà mọi phép so sánh với `NaN` đều false nên luật
`Count ≥ 1` không bắt được. Khi xuất ra JSON, `NaN` trở thành **`null`**.
`stats.totalSheets` cũng thành `null` theo.

**Cách chặn:** kiểm `stats.totalSheets` là số nguyên hợp lệ trước khi ghi file,
hoặc ép `Count` sang số ở phía bạn trước khi gửi.

**Khuyến nghị chung:** gửi đúng kiểu ngay từ đầu. `"false"` thành `true` và
`"abc"` thành `null` đều là bẫy hay gặp khi dữ liệu đi qua form HTML hoặc CSV.

---

## 7. `warnings` — cạm bẫy lớn nhất khi gọi bằng máy

Vì mọi trường đều tuỳ chọn, gửi lên một file gần như rỗng vẫn nhận `200 OK`
kèm cấu hình trông hoàn chỉnh — nhưng phần lớn nội dung là **dữ liệu mẫu**.

Gửi đúng `{"Workset":{"Name":"91.LINK CAD"}}` nhận về:

```json
"warnings": [
  "Thiếu nhóm TitleBlock, đã dùng toàn bộ giá trị mặc định.",
  "Thiếu nhóm Keyplan, đã dùng toàn bộ giá trị mặc định.",
  "Thiếu nhóm Grid, đã dùng toàn bộ giá trị mặc định.",
  "Thiếu nhóm Viewport, đã dùng toàn bộ giá trị mặc định.",
  "Thiếu nhóm DualView, đã dùng toàn bộ giá trị mặc định.",
  "Thiếu nhóm ViewSplitter, đã dùng toàn bộ giá trị mặc định.",
  "PackageTypes thiếu hoặc không phải mảng, đã dùng 3 bộ bản vẽ mẫu của template."
]
```

Dòng cuối nguy hiểm nhất: **3 bộ bản vẽ hoàn toàn không phải của người gọi** đã
được ghi vào file kết quả, và `ok` vẫn là `true`.

**Bắt buộc với hệ thống tự động:** dùng `?strict=1`, hoặc từ chối kết quả khi
`warnings` không rỗng. Chỉ để chế độ dễ dãi khi có người ngồi xem.

### Danh mục `warnings`

| Tình huống | Mẫu thông báo |
|---|---|
| Thiếu cả nhóm | `Thiếu nhóm <Nhóm>, đã dùng toàn bộ giá trị mặc định.` |
| Nhóm sai kiểu | `Nhóm <Nhóm> không phải object, đã dùng toàn bộ giá trị mặc định.` |
| Nhóm thiếu vài trường | `Nhóm <Nhóm> thiếu field: a, b, c.` |
| Thiếu `PackageTypes` | `PackageTypes thiếu hoặc không phải mảng, đã dùng 3 bộ bản vẽ mẫu của template.` |
| Phần tử bộ sai kiểu | `PackageTypes[<i>] không phải object, đã thay bằng bộ rỗng mặc định.` |
| Bộ thiếu `Key` | `PackageTypes[<i>] thiếu Key, đã đặt thành “Package<n>”.` |
| Bộ thiếu `DisplayName` | `PackageTypes[<i>] thiếu DisplayName, đã đặt thành “Bộ bản vẽ <n>”.` |
| Bộ thiếu `ModelGroupPatterns` | `PackageTypes[<i>] thiếu ModelGroupPatterns, đã đặt thành mảng rỗng.` |
| Bộ thiếu `Sheets` | `PackageTypes[<i>] thiếu Sheets, đã đặt thành mảng rỗng.` |

---

## 8. `issues` — 7 luật kiểm tra

Vi phạm bất kỳ luật nào → `422`.

| # | Luật | Thông báo |
|---|---|---|
| 1 | `ViewSplitter.ScaleMin` ≤ `ViewSplitter.ScaleMax` | `ScaleMin phải nhỏ hơn hoặc bằng ScaleMax.` |
| 2 | `Keyplan.HighlightColorHex` khớp `^[0-9A-Fa-f]{6}$` sau khi bỏ `#` | `Màu highlight phải có đúng 6 ký tự HEX.` |
| 3 | `DualView.ViewGapMm` ≥ 0 | `Khoảng cách giữa hai view không được âm.` |
| 4 | Có sheet `SourceType = "Cad"` thì `Workset.Name` không được rỗng sau `trim()` | `Các sheet nguồn Cad cần Workset.Name để link CAD vào đúng workset.` |
| 5 | Các `Key` không rỗng phải đôi một khác nhau | `Key của các bộ bản vẽ phải là duy nhất.` |
| 6 | Mỗi bộ phải có `Key` không rỗng | `Bộ “<DisplayName>” đang thiếu Key.` |
| 7 | Mọi sheet phải có `Count` ≥ 1 | `Bộ “<DisplayName>” có sheet với Count nhỏ hơn 1.` |

Luật 6 và 7 lặp lại cho từng bộ vi phạm, nên `issues` có thể chứa nhiều dòng
cùng dạng.

### ⚠️ Thông báo không có mã ổn định

`issues` và `warnings` là **chuỗi tiếng Việt dành cho người đọc**, không phải mã
lỗi. Chúng có thể đổi cách diễn đạt ở phiên bản sau.

**Đừng so khớp chuỗi chính xác.** Hãy quyết định dựa trên:

- mã HTTP (`200` / `400` / `422` / `413` / `503`),
- `issues.length === 0` hay không,
- `warnings.length === 0` hay không.

Nếu buộc phải phân loại chi tiết, hãy dùng `indexOf` với một mẩu ổn định
(`"ScaleMin"`, `"HEX"`, `"PackageTypes"`) thay vì so bằng cả câu.

### Mẫu `422` thật

```json
{
  "ok": false,
  "issues": [
    "ScaleMin phải nhỏ hơn hoặc bằng ScaleMax.",
    "Màu highlight phải có đúng 6 ký tự HEX.",
    "Key của các bộ bản vẽ phải là duy nhất.",
    "Bộ “Bộ bản vẽ 1” có sheet với Count nhỏ hơn 1."
  ],
  "stats": {"packages": 2, "totalSheets": 0, "requiredSheets": 0, "cadSheets": 0}
}
```

---

## 9. Xử lý JSONC

`cleanJsonc` quét từng ký tự và có trạng thái chuỗi, nên **không** phá hỏng nội
dung nằm trong dấu nháy.

| Cú pháp | Xử lý |
|---|---|
| `// đến hết dòng` | Xoá, thay bằng xuống dòng |
| `/* … */` | Xoá |
| `,` ngay trước `}` hoặc `]` (bỏ qua khoảng trắng) | Xoá |
| `//` nằm **trong** chuỗi | **Giữ nguyên** — `"https://a//b"` an toàn |
| `\"` escape trong chuỗi | Hiểu đúng, không kết thúc chuỗi sớm |

Không hỗ trợ: dấu nháy đơn, khoá không có nháy, `NaN`/`Infinity` — đó là JSON5,
không phải JSONC. Gặp những thứ này sẽ trả `400`.

---

## 10. Các endpoint còn lại

### `POST /validate`

Body là JSON config đã có (không phải JSONC — dùng `JSON.parse` trực tiếp).

```json
{"ok": false,
 "issues": ["Khoảng cách giữa hai view không được âm."],
 "stats": {"packages": 3, "totalSheets": 25, "requiredSheets": 20, "cadSheets": 11}}
```

`200` khi `issues` rỗng, `422` khi không, `400` khi body không phải JSON object.
Endpoint này **không** trả `config` và **không** áp dụng `warnings`.

### `GET /template`

Trả về nguyên object cấu hình mặc định: 3 bộ (`CanHo`, `HanhlangFCU`,
`HanhlangHVAC`), tổng 25 sheet, 6488 byte. Dùng làm điểm xuất phát cho form.

### `GET /health`

```json
{"ok": true, "version": "0.1.0", "time": "2026-07-31T09:11:22.824Z"}
```

`503` kèm chẩn đoán nếu server thiếu Node runtime.

---

## 11. Mã ví dụ

### C# — add-in Revit

```csharp
using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json;

public sealed class SheetConfigInvalidException : Exception
{
    public IReadOnlyList<string> Issues { get; }
    public SheetConfigInvalidException(IReadOnlyList<string> issues)
        : base(string.Join("\n", issues)) => Issues = issues;
}

public static class SheetConfigClient
{
    private static readonly HttpClient Http = new()
    {
        BaseAddress = new Uri("https://tranphuc120203-boc-tach-ban-ve.hf.space"),
        Timeout = TimeSpan.FromSeconds(90)   // Space ngủ thì request đầu chậm
    };

    /// <summary>Trả về chuỗi JSON chuẩn, ghi thẳng ra đĩa được.</summary>
    public static async Task<string> ChuanHoaAsync(string noiDungJsonc)
    {
        using var body = new StringContent(noiDungJsonc, Encoding.UTF8, "text/plain");
        using var res = await Http.PostAsync("/api/sheet-config/normalize?strict=1", body);

        var raw = await res.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(raw);
        var root = doc.RootElement;

        if (res.StatusCode == HttpStatusCode.UnprocessableEntity)
        {
            var issues = root.GetProperty("issues").EnumerateArray()
                             .Select(x => x.GetString() ?? "").ToList();
            throw new SheetConfigInvalidException(issues);
        }

        if (!res.IsSuccessStatusCode)
        {
            var msg = root.TryGetProperty("error", out var e) ? e.GetString() : raw;
            throw new HttpRequestException($"HTTP {(int)res.StatusCode}: {msg}");
        }

        // KHÔNG serialize lại từ "config" — sẽ mất các đảm bảo ở mục 4.
        return root.GetProperty("json").GetString()!;
    }

    public static async Task GhiRaFileAsync(string nguon, string dich)
    {
        var json = await ChuanHoaAsync(await File.ReadAllTextAsync(nguon, Encoding.UTF8));
        await File.WriteAllTextAsync(dich, json, new UTF8Encoding(false)); // không BOM
    }

    /// <summary>Đánh thức Space lúc khởi động ứng dụng.</summary>
    public static async Task DanhThucAsync()
    {
        try { await Http.GetAsync("/api/sheet-config/health"); } catch { }
    }
}
```

### Python

```python
import requests

BASE = "https://tranphuc120203-boc-tach-ban-ve.hf.space"


class CauHinhSai(ValueError):
    """Dữ liệu người dùng sai — không retry."""
    def __init__(self, issues: list[str]):
        super().__init__("\n".join(issues))
        self.issues = issues


def chuan_hoa(noi_dung: str, strict: bool = True) -> str:
    r = requests.post(
        f"{BASE}/api/sheet-config/normalize",
        params={"strict": "1"} if strict else None,
        data=noi_dung.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        timeout=90,
    )
    d = r.json()

    if r.status_code in (400, 413, 422):
        raise CauHinhSai(d.get("issues") or [d.get("error", "")])
    r.raise_for_status()          # 503 và lỗi khác -> retry được
    return d["json"]


if __name__ == "__main__":
    with open("DocumentSetConfig.jsonc", encoding="utf-8") as f:
        ket_qua = chuan_hoa(f.read())
    with open("DocumentSetConfig.json", "w", encoding="utf-8") as f:
        f.write(ket_qua)
```

### PowerShell

```powershell
$base = "https://tranphuc120203-boc-tach-ban-ve.hf.space"
$noiDung = Get-Content -Raw -Encoding UTF8 .\DocumentSetConfig.jsonc

try {
    $res = Invoke-RestMethod -Method Post `
        -Uri "$base/api/sheet-config/normalize?strict=1" `
        -ContentType "text/plain; charset=utf-8" `
        -Body ([Text.Encoding]::UTF8.GetBytes($noiDung)) `
        -TimeoutSec 90

    [IO.File]::WriteAllText((Join-Path $PWD "DocumentSetConfig.json"),
        $res.json, (New-Object Text.UTF8Encoding $false))
    Write-Host "OK — $($res.stats.packages) bộ, $($res.stats.totalSheets) sheet"
}
catch {
    ($_.ErrorDetails.Message | ConvertFrom-Json).issues | ForEach-Object { Write-Error $_ }
}
```

### JavaScript / TypeScript

```ts
const BASE = "https://tranphuc120203-boc-tach-ban-ve.hf.space";

export class CauHinhSai extends Error {
  constructor(readonly issues: string[]) { super(issues.join("\n")); }
}

export async function chuanHoa(noiDung: string, strict = true): Promise<string> {
  const url = `${BASE}/api/sheet-config/normalize${strict ? "?strict=1" : ""}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "text/plain" },
    body: noiDung,
  });
  const data = await res.json();

  if ([400, 413, 422].includes(res.status)) {
    throw new CauHinhSai(data.issues ?? [data.error]);
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);  // 503 -> retry được

  return data.json;
}
```

---

## 12. Bài kiểm tra tự đối chiếu

Chạy sau khi tích hợp xong để chắc chắn client của bạn hành xử đúng. Dùng file
`TEMPLATE_DocumentSetConfig.json` của repo `json-to-sheet` làm input chuẩn.

| # | Input | Kỳ vọng |
|---|---|---|
| 1 | File template (JSONC đầy đủ) | `200`, `issues: []`, `warnings: []`, `stats.packages = 3`, `totalSheets = 25`, `requiredSheets = 20`, `cadSheets = 11` |
| 2 | Kết quả bước 1 gửi lại | Trả về **đúng chuỗi `json` giống hệt** — kiểm tính idempotent |
| 3 | `[]` | `400`, `error` chứa `"object JSON"` |
| 4 | `{"ViewSplitter":{"ScaleMin":200,"ScaleMax":50}}` | `422`, `issues` chứa `"ScaleMin"` |
| 5 | `{"Workset":{"Name":"X"}}` **không** `strict` | `200` nhưng `warnings` **không rỗng** — client phải chặn được |
| 6 | Như bước 5 **có** `strict=1` | `422` |
| 7 | Body > 2 MB | `413` |

Đầu ra của bước 1 phải khớp chính xác:

```
độ dài  : 6686 byte
sha256  : 8e209330aa089b6fc48de34dd4fa37a208138a52181a02c9d2c5069dbbff665f
```

```bash
curl -s -X POST --data-binary @TEMPLATE_DocumentSetConfig.json \
  -H 'Content-Type: text/plain' \
  'https://tranphuc120203-boc-tach-ban-ve.hf.space/api/sheet-config/normalize' \
  | python3 -c "import sys,json,hashlib; j=json.load(sys.stdin)['json'].encode(); \
print(len(j), hashlib.sha256(j).hexdigest())"
```

Nếu hash khớp thì client của bạn đọc đúng trường, giữ đúng encoding, và không
serialize lại nhầm.

---

## 13. Danh sách kiểm tra khi tích hợp

- [ ] Bật `?strict=1`, hoặc từ chối khi `warnings` không rỗng
- [ ] Ghi thẳng trường `json`, **không** serialize lại từ `config`
- [ ] Timeout ≥ 90 giây
- [ ] Retry chỉ với `503` và lỗi mạng; **không** retry `400`/`413`/`422`
- [ ] Đọc/ghi file UTF-8 **không BOM**
- [ ] Hiện `issues` nguyên văn cho người dùng
- [ ] Quyết định theo mã HTTP và độ dài mảng, không so khớp chuỗi thông báo
- [ ] Gọi `/health` lúc khởi động để đánh thức Space
- [ ] Chạy 7 bước ở mục 12 và đối chiếu hash

---

## 14. Vận hành

**Space ngủ sau 48 giờ không dùng.** Request đầu sau khi ngủ mất ~30 giây khởi
động container. Đặt timeout ≥ 90 giây và gọi `/health` trước khi làm việc thật.

**Hiệu năng bình thường:** ~1 giây/request qua internet, gồm ~80ms khởi động
tiến trình Node phía server.

**Giới hạn:** body 2 MB. Không giới hạn tần suất, nhưng Space chạy CPU chia sẻ —
tránh bắn song song hàng loạt.

**Không có xác thực.** Ai biết URL đều gọi được. Dịch vụ không lưu gì nên không
rò rỉ dữ liệu cũ, nhưng nội dung gửi lên **có đi qua máy chủ Hugging Face** —
cân nhắc nếu cấu hình chứa thông tin dự án nhạy cảm.

---

## 15. Khắc phục sự cố

| Hiện tượng | Nguyên nhân | Xử lý |
|---|---|---|
| `/json-to-sheet` ra giao diện bóc tách | Cache trình duyệt cũ | Tải lại bỏ cache (`Ctrl+Shift+R` / `Cmd+Shift+R`) |
| Request đầu timeout | Space đang ngủ | Timeout 90s, gọi `/health` trước |
| `503` `"Không tìm thấy Node trong image"` | Dockerfile thiếu dòng copy binary node | Xem [backend/app/sheet_config/README.md](backend/app/sheet_config/README.md) |
| `400` với file mở được bằng Notepad | File có BOM, hoặc top-level không phải object | Ký tự đầu phải là `{`, lưu UTF-8 không BOM |
| Tiếng Việt thành `?????` | Client không dùng UTF-8 | Ép UTF-8 cả hai chiều |
| Hash khác mục 12 | Đã serialize lại từ `config` | Dùng thẳng chuỗi `json` |
| `200` nhưng nội dung lạ | Quên `strict=1`, server đã bù dữ liệu mẫu | Bật `strict=1`, đọc `warnings` |
| `IsRequired` sai | Gửi chuỗi `"false"` → `Boolean("false")` là `true` | Gửi bool thật, không gửi chuỗi |
| `Count` ra `null`, `totalSheets` ra `null` | Gửi `Count` không phải số | Ép sang số trước khi gửi (mục 6) |
| Bubble dưới không ăn | Gửi `ShowBubbleBottom` | Đúng tên là `ShowBubbleBotton` (mục 5) |

---

## 16. Nguồn gốc mã

Logic nằm ở repo `json-to-sheet`, đóng gói thành
`backend/app/sheet_config/js/api-cli.mjs`. **Giao diện web và API này chạy chung
đúng một đoạn mã** — đã đối chiếu byte-for-byte trên file template chuẩn.

Tầng Python (`runner.py`, `router.py`) không chứa logic nghiệp vụ nào, chỉ gọi
tiến trình Node rồi chuyển tiếp nguyên trạng status và body.

Cách cập nhật logic và giao diện: xem
[backend/app/sheet_config/README.md](backend/app/sheet_config/README.md).
