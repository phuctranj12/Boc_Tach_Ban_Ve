# Sheet Configure API — hướng dẫn tích hợp

API chuẩn hoá cấu hình bộ bản vẽ shop (`DocumentSetConfig`): nhận JSON/JSONC
tuỳ tiện, trả về JSON hợp lệ kèm cảnh báo và thống kê.

> **Không liên quan tới API bóc tách bản vẽ.** Hai luồng chỉ dùng chung một chỗ
> deploy. API bóc tách xem [API_DOCS.md](API_DOCS.md).

**Base URL**

```
https://tranphuc120203-boc-tach-ban-ve.hf.space
```

Mọi endpoint nằm dưới prefix `/api/sheet-config`. Không cần xác thực. CORS mở
cho mọi origin nên gọi thẳng từ trình duyệt được.

**Giao diện web cho người dùng cuối**

```
https://tranphuc120203-boc-tach-ban-ve.hf.space/json-to-sheet
```

Dành cho người ngồi chỉnh tay: mô phỏng tờ giấy A1/A3, kéo thả sắp xếp trình tự
sheet, nhập số ngay trên đường kích thước. Giao diện chạy **hoàn toàn trong trình
duyệt**, không gọi API này — cấu hình không rời khỏi máy người dùng.

Tài liệu dưới đây dành cho việc gọi bằng máy.

---

## 1. Dịch vụ này giải quyết việc gì

File cấu hình gốc thường được viết tay nên là **JSONC** chứ không phải JSON:
có chú thích `//`, `/* */`, và dấu phẩy thừa trước `}` `]`. Thư viện JSON chuẩn
của C#, Python hay Java đều không đọc được.

API này làm ba việc, theo đúng thứ tự:

```
JSONC thô  ──▶  bỏ chú thích + dấu phẩy thừa  ──▶  bù giá trị mặc định
                                                          │
              JSON hợp lệ, UTF-8  ◀── kiểm tra 6 luật ◀────┘
```

Dịch vụ **stateless** — không lưu gì, không có session, không có ID. Gửi lên
cái gì thì nhận lại đúng cái đó sau khi xử lý.

---

## 2. Endpoint

| Method | Path | Việc |
|---|---|---|
| `GET` | `/api/sheet-config/health` | Kiểm tra sống |
| `GET` | `/api/sheet-config/template` | Lấy cấu hình mẫu đầy đủ |
| `POST` | `/api/sheet-config/normalize` | JSONC → JSON chuẩn (endpoint chính) |
| `POST` | `/api/sheet-config/validate` | Chỉ kiểm tra luật |

### 2.1 `POST /normalize`

Endpoint bạn sẽ dùng 90% thời gian.

**Gửi lên** — chọn một trong hai cách:

| Cách | `Content-Type` | Body |
|---|---|---|
| Thô (khuyến nghị) | `text/plain` | Nguyên văn file `.json` / `.jsonc` |
| Bọc | `application/json` | `{"source": "…nội dung file…"}` |

Cách thô tiện hơn vì không phải escape chuỗi. Cách bọc dùng khi client của bạn
bắt buộc gửi JSON.

**Query tuỳ chọn**

| Query | Mặc định | Tác dụng |
|---|---|---|
| `strict=1` | tắt | Coi mọi cảnh báo là lỗi → trả `422` thay vì `200` |
| `pretty=0` | bật | Trường `json` xuất một dòng thay vì thụt lề 2 khoảng trắng |

**Nhận về**

```jsonc
{
  "ok": true,
  "config": { /* object cấu hình đã chuẩn hoá */ },
  "json": "{\n  \"TitleBlock\": {\n    \"TitleBlockWidthMm\": 51,\n …",
  "issues": [],
  "warnings": [],
  "stats": {
    "packages": 3,
    "totalSheets": 25,
    "requiredSheets": 20,
    "cadSheets": 11
  }
}
```

| Trường | Ý nghĩa |
|---|---|
| `ok` | `true` khi `issues` rỗng |
| `config` | Cấu hình dạng object, dùng khi bạn muốn đọc/sửa tiếp bằng code |
| `json` | **Chuỗi để ghi thẳng ra file.** Đây là thứ bạn cần trong hầu hết trường hợp |
| `issues` | Lỗi chặn xuất file. Rỗng thì dùng được |
| `warnings` | Chỗ server đã tự bù giá trị mặc định — **đọc kỹ mục 4** |
| `stats` | Thống kê nhanh để hiển thị hoặc đối soát |

Ghi `json` ra file là xong, **không cần serialize lại** `config`. Serialize lại
bằng thư viện của ngôn ngữ khác có thể ra kết quả khác (thứ tự khoá, cách in số
thực), còn `json` là đúng chuỗi mà bản web sinh ra.

### 2.2 `POST /validate`

Gửi lên một cấu hình JSON đã có, chỉ kiểm tra luật, không trả về config.

```jsonc
{ "ok": false, "issues": ["Khoảng cách giữa hai view không được âm."], "stats": { … } }
```

### 2.3 `GET /template`

Trả về cấu hình mẫu đầy đủ (3 bộ bản vẽ, 25 sheet). Dùng để dựng form ban đầu
hoặc làm điểm xuất phát cho người dùng mới.

### 2.4 `GET /health`

```json
{ "ok": true, "version": "0.1.0", "time": "2026-07-31T08:50:04.545Z" }
```

---

## 3. Mã trạng thái

| Mã | Nghĩa | Xử lý phía client |
|---|---|---|
| `200` | Hợp lệ | Lấy `json`, ghi ra file |
| `422` | Đọc được nhưng vi phạm luật | Hiện `issues` cho người dùng sửa. **Vẫn có `config`** để họ xem dữ liệu đã chuẩn hoá |
| `400` | Không parse được, hoặc top-level không phải object JSON | Báo file hỏng. Đọc `error` |
| `413` | Body vượt 2 MB | Từ chối từ phía client trước khi gửi |
| `503` | Server thiếu Node runtime | Lỗi hạ tầng, báo quản trị. Không phải lỗi dữ liệu |

`422` **không phải lỗi hệ thống** — nó nghĩa là file đọc được nhưng cấu hình
sai. Đừng retry, hãy hiện `issues` ra cho người dùng.

Với `400` và `503`, body có dạng `{"ok": false, "error": "…"}`.

---

## 4. Cạm bẫy quan trọng nhất: `warnings`

Mọi trường trong cấu hình đều **tuỳ chọn**. Thiếu trường nào server tự bù giá
trị mặc định. Điều đó rất tiện cho giao diện web, nhưng **nguy hiểm khi gọi
bằng máy**: gửi lên một file gần như rỗng, bạn vẫn nhận `200 OK` kèm một cấu
hình trông hoàn chỉnh — nhưng phần lớn nội dung là dữ liệu mẫu, không phải của
bạn.

Ví dụ, gửi lên đúng một dòng `{"Workset":{"Name":"91.LINK CAD"}}`:

```json
"warnings": [
  "Thiếu nhóm TitleBlock, đã dùng toàn bộ giá trị mặc định.",
  "Thiếu nhóm Keyplan, đã dùng toàn bộ giá trị mặc định.",
  "Thiếu nhóm Grid, đã dùng toàn bộ giá trị mặc định.",
  "PackageTypes thiếu hoặc không phải mảng, đã dùng 3 bộ bản vẽ mẫu của template."
]
```

Dòng cuối đặc biệt đáng sợ: **3 bộ bản vẽ hoàn toàn không phải của bạn** đã
được chèn vào.

**Nguyên tắc tích hợp:** hệ thống tự động thì luôn dùng `?strict=1`, hoặc kiểm
tra `warnings` rỗng trước khi ghi file. Chỉ để chế độ dễ dãi cho luồng có người
ngồi xem kết quả.

---

## 5. Hợp đồng dữ liệu đầu vào

| Điều kiện | Chi tiết |
|---|---|
| Top-level | Phải là **object**. Mảng, số, chuỗi → `400` |
| Cú pháp | JSONC hợp lệ: `//`, `/* */`, dấu phẩy thừa đều được chấp nhận |
| Mọi trường | Tuỳ chọn — thiếu thì bù mặc định và ghi vào `warnings` |
| Trường lạ | **Giữ nguyên**, đi thẳng ra output. Bạn có thể nhét metadata riêng vào mà không sợ mất |
| Encoding | UTF-8. Tiếng Việt không bị escape thành `\uXXXX` |

Cấu trúc gồm 7 nhóm cấu hình + 1 mảng bộ bản vẽ:

| Nhóm | Trường chính |
|---|---|
| `TitleBlock` | `TitleBlockWidthMm`, `SheetMarginLeftMm/Right/Top/Bottom` |
| `Keyplan` | `Anchor` (`TopLeft`\|`TopRight`\|`BottomLeft`\|`BottomRight`), `OffsetXMm/Y`, `CanvasWidthMm/Height`, `HighlightColorHex`, `ViewTemplateName` |
| `Grid` | `EnableGridTrim`, `BubbleExtensionMm`, `ShowBubbleTop/Botton/Right/Left` |
| `Viewport` | `MinClearanceMm`, `AutoRotateAspectRatio` |
| `DualView` | `Enabled`, `ViewGapMm`, `PreferHorizontal` |
| `ViewSplitter` | `ExtentPaddingXMm/Y`, `ScaleMin/Max/Step`, `MinFillRatio`, `MinTilePaperMm`, `UseEnhancedLogic` |
| `Workset` | `Name` |
| `PackageTypes[]` | `Key`, `DisplayName`, `ModelGroupPatterns[]`, `Sheets[]` |

Mỗi phần tử `Sheets[]`:

```jsonc
{
  "DrawingType": "MatBangThiCong",   // ToBia | ToLot | DanhMucBanVe | Legend
                                     // MatBangCombine | MatBangThiCong
                                     // SoDoNguyenLy | ChiTietLapDat
  "SourceType": "Blank",             // Cover | Index | Cad | Blank
  "DisplayName": "Mặt bằng",
  "Count": 1,
  "IsRequired": true
}
```

Giá trị mặc định khi thiếu: `DrawingType` → `"NewDrawing"`, `SourceType` →
`"Blank"`, `DisplayName` → `"Bản vẽ mới"`, `Count` → `1`, `IsRequired` → `true`.

---

## 6. Sáu luật kiểm tra

Vi phạm bất kỳ luật nào → `422`:

1. `ViewSplitter.ScaleMin` ≤ `ViewSplitter.ScaleMax`
2. `Keyplan.HighlightColorHex` đúng 6 ký tự HEX (có hoặc không có `#`)
3. `DualView.ViewGapMm` không âm
4. Nếu có sheet `SourceType = "Cad"` thì `Workset.Name` không được rỗng
5. `Key` của các bộ bản vẽ phải duy nhất và không rỗng
6. Mọi sheet phải có `Count` ≥ 1

---

## 7. Ví dụ theo ngôn ngữ

### curl

```bash
curl -X POST \
  --data-binary @DocumentSetConfig.jsonc \
  -H 'Content-Type: text/plain' \
  'https://tranphuc120203-boc-tach-ban-ve.hf.space/api/sheet-config/normalize?strict=1'
```

### C# — add-in Revit

```csharp
using System.Net.Http;
using System.Text;
using System.Text.Json;

static readonly HttpClient Http = new HttpClient
{
    BaseAddress = new Uri("https://tranphuc120203-boc-tach-ban-ve.hf.space"),
    Timeout = TimeSpan.FromSeconds(60)   // Space ngủ thì request đầu chậm
};

public static async Task<string> ChuanHoaCauHinh(string duongDanFile)
{
    var noiDung = await File.ReadAllTextAsync(duongDanFile, Encoding.UTF8);
    var body = new StringContent(noiDung, Encoding.UTF8, "text/plain");

    var res = await Http.PostAsync("/api/sheet-config/normalize?strict=1", body);
    var raw = await res.Content.ReadAsStringAsync();
    using var doc = JsonDocument.Parse(raw);
    var root = doc.RootElement;

    if (res.StatusCode == HttpStatusCode.UnprocessableEntity)
    {
        var loi = root.GetProperty("issues").EnumerateArray()
                      .Select(x => x.GetString());
        throw new InvalidOperationException(
            "Cấu hình sai:\n" + string.Join("\n", loi));
    }

    if (!res.IsSuccessStatusCode)
        throw new HttpRequestException(
            root.TryGetProperty("error", out var e) ? e.GetString() : raw);

    // Ghi thẳng chuỗi này ra file, KHÔNG serialize lại từ "config".
    return root.GetProperty("json").GetString();
}
```

### Python

```python
import requests

BASE = "https://tranphuc120203-boc-tach-ban-ve.hf.space"

def chuan_hoa(duong_dan: str) -> str:
    with open(duong_dan, encoding="utf-8") as f:
        noi_dung = f.read()

    r = requests.post(
        f"{BASE}/api/sheet-config/normalize",
        params={"strict": "1"},
        data=noi_dung.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        timeout=60,
    )
    d = r.json()

    if r.status_code == 422:
        raise ValueError("Cấu hình sai:\n" + "\n".join(d["issues"]))
    r.raise_for_status()

    return d["json"]


with open("DocumentSetConfig.json", "w", encoding="utf-8") as f:
    f.write(chuan_hoa("TEMPLATE_DocumentSetConfig.json"))
```

### PowerShell

```powershell
$base = "https://tranphuc120203-boc-tach-ban-ve.hf.space"
$noiDung = Get-Content -Raw -Encoding UTF8 .\DocumentSetConfig.jsonc

try {
    $res = Invoke-RestMethod -Method Post `
        -Uri "$base/api/sheet-config/normalize?strict=1" `
        -ContentType "text/plain; charset=utf-8" `
        -Body ([Text.Encoding]::UTF8.GetBytes($noiDung))

    [IO.File]::WriteAllText("DocumentSetConfig.json", $res.json, [Text.Encoding]::UTF8)
    Write-Host "OK — $($res.stats.totalSheets) sheet"
}
catch {
    $loi = $_.ErrorDetails.Message | ConvertFrom-Json
    Write-Error ($loi.issues -join "`n")
}
```

### JavaScript / trình duyệt

```js
const BASE = "https://tranphuc120203-boc-tach-ban-ve.hf.space";

async function chuanHoa(file) {
  const res = await fetch(`${BASE}/api/sheet-config/normalize?strict=1`, {
    method: "POST",
    headers: { "Content-Type": "text/plain" },
    body: await file.text(),
  });
  const data = await res.json();

  if (res.status === 422) throw new Error(data.issues.join("\n"));
  if (!res.ok) throw new Error(data.error);

  return data.json;
}
```

---

## 8. Vận hành

**Space ngủ sau 48 giờ không ai dùng.** Request đầu tiên sau khi ngủ mất khoảng
30 giây để container khởi động lại. Đặt timeout client tối thiểu 60 giây, hoặc
gọi `/api/sheet-config/health` để đánh thức trước khi làm việc thật.

**Hiệu năng bình thường:** khoảng 1 giây cho một request qua internet, đã bao
gồm ~80ms khởi động tiến trình Node phía server.

**Giới hạn:** body tối đa 2 MB. Không có giới hạn tần suất, nhưng Space chạy
CPU chia sẻ nên đừng gọi song song hàng loạt.

**Không có xác thực.** Ai biết URL đều gọi được. Dịch vụ không lưu gì nên không
rò rỉ dữ liệu cũ, nhưng nội dung bạn gửi lên có đi qua máy chủ Hugging Face —
cân nhắc nếu cấu hình chứa thông tin dự án nhạy cảm.

---

## 9. Khi gặp sự cố

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `503` kèm `"Không tìm thấy Node trong image"` | Dockerfile thiếu dòng copy binary node | Xem [backend/app/sheet_config/README.md](backend/app/sheet_config/README.md) |
| Request đầu timeout | Space đang ngủ | Tăng timeout lên 60s, hoặc gọi `/health` trước |
| `400` với file mở được bằng Notepad | File có BOM hoặc không phải object ở top-level | Kiểm tra ký tự đầu file phải là `{` |
| Tiếng Việt thành `?????` | Client không gửi/đọc UTF-8 | Ép UTF-8 ở cả hai chiều |
| JSON trả về khác bản web | Đã serialize lại từ `config` | Dùng thẳng chuỗi `json` |

---

## 10. Nguồn gốc mã

Logic nằm ở repo `json-to-sheet`, đóng gói thành
`backend/app/sheet_config/js/api-cli.mjs`. **Bản web và API này chạy chung đúng
một đoạn mã**, đã đối chiếu cho ra kết quả giống nhau từng byte
(`sha256:8e209330aa089b6f…`, 6686 bytes trên file template chuẩn).

Cách cập nhật logic: xem
[backend/app/sheet_config/README.md](backend/app/sheet_config/README.md).
