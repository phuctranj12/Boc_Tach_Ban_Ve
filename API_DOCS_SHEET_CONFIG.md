# Sheet Configure API — hướng dẫn tích hợp

API chuẩn hoá cấu hình bộ bản vẽ shop (`DocumentSetConfig`): nhận JSON/JSONC
viết tay tuỳ tiện, trả về JSON hợp lệ kèm cảnh báo và thống kê.

> **Không liên quan tới API bóc tách bản vẽ.** Hai luồng chỉ dùng chung một chỗ
> deploy. API bóc tách xem [API_DOCS.md](API_DOCS.md).

---

## Bắt đầu trong 30 giây

```bash
curl -X POST \
  --data-binary @DocumentSetConfig.jsonc \
  -H 'Content-Type: text/plain' \
  'https://tranphuc120203-boc-tach-ban-ve.hf.space/api/sheet-config/normalize?strict=1'
```

Lấy trường `json` trong phản hồi, ghi thẳng ra file. Xong.

| | |
|---|---|
| **Base URL** | `https://tranphuc120203-boc-tach-ban-ve.hf.space` |
| **Prefix** | `/api/sheet-config` |
| **Xác thực** | Không cần |
| **CORS** | Mở cho mọi origin — gọi thẳng từ trình duyệt được |
| **Swagger** | [`/docs`](https://tranphuc120203-boc-tach-ban-ve.hf.space/docs) — bấm thử ngay trên trình duyệt |
| **OpenAPI** | [`/openapi.json`](https://tranphuc120203-boc-tach-ban-ve.hf.space/openapi.json) — sinh client tự động |
| **Giao diện người dùng** | [`/json-to-sheet`](https://tranphuc120203-boc-tach-ban-ve.hf.space/json-to-sheet) |

Giao diện web dành cho người ngồi chỉnh tay: mô phỏng tờ giấy A1/A3, kéo thả sắp
xếp trình tự sheet, nhập số ngay trên đường kích thước. Nó chạy **hoàn toàn trong
trình duyệt, không gọi API này** — cấu hình không rời khỏi máy người dùng.

---

## 1. Vấn đề mà API này giải quyết

File cấu hình gốc thường viết tay nên là **JSONC** chứ không phải JSON: có chú
thích `//`, `/* */`, và dấu phẩy thừa trước `}` `]`. `System.Text.Json` của C#,
`json` của Python, `Jackson` của Java đều ném exception khi gặp.

```
JSONC thô  ──▶  bỏ chú thích + dấu phẩy thừa  ──▶  bù giá trị mặc định
                                                          │
              JSON hợp lệ, UTF-8  ◀── kiểm tra 6 luật ◀────┘
```

Dịch vụ **stateless**: không lưu gì, không session, không job ID. Cùng một input
luôn cho cùng một output, nên **retry an toàn tuyệt đối** — không sợ tạo trùng
hay hỏng trạng thái.

---

## 2. Chọn endpoint nào

| Bạn muốn | Dùng |
|---|---|
| Đọc file `.jsonc` người dùng đưa, xuất ra `.json` sạch | `POST /normalize` |
| Kiểm tra cấu hình đã có còn hợp lệ không, không cần sửa | `POST /validate` |
| Dựng form/UI mặc định cho người dùng mới | `GET /template` |
| Kiểm tra dịch vụ còn sống, hoặc đánh thức Space | `GET /health` |

Hầu hết tích hợp chỉ cần `POST /normalize`.

---

## 3. `POST /normalize`

### Gửi lên

Chọn một trong hai cách, kết quả như nhau:

| Cách | `Content-Type` | Body |
|---|---|---|
| **Thô** (khuyến nghị) | `text/plain` | Nguyên văn file, không escape gì cả |
| Bọc | `application/json` | `{"source": "…nội dung file…"}` |

Dùng cách thô trừ khi client của bạn bắt buộc gửi JSON.

### Query

| Query | Mặc định | Tác dụng |
|---|---|---|
| `strict=1` | tắt | Coi mọi cảnh báo là lỗi → `422` thay vì `200`. **Hệ thống tự động nên luôn bật** |
| `pretty=0` | bật | Trường `json` xuất một dòng thay vì thụt lề 2 khoảng trắng |

### Nhận về

```jsonc
{
  "ok": true,
  "config": { /* object cấu hình đã chuẩn hoá */ },
  "json": "{\n  \"TitleBlock\": {\n    \"TitleBlockWidthMm\": 51,\n …",
  "issues": [],
  "warnings": [],
  "stats": { "packages": 3, "totalSheets": 25, "requiredSheets": 20, "cadSheets": 11 }
}
```

| Trường | Kiểu | Dùng để |
|---|---|---|
| `ok` | bool | `true` khi `issues` rỗng |
| `config` | object | Đọc/sửa tiếp bằng code |
| `json` | string | **Ghi thẳng ra file.** Thứ bạn cần trong hầu hết trường hợp |
| `issues` | string[] | Lỗi chặn xuất file — hiện cho người dùng sửa |
| `warnings` | string[] | Chỗ server đã tự bù mặc định — **đọc mục 6** |
| `stats` | object | `packages`, `totalSheets`, `requiredSheets`, `cadSheets` |

> **Ghi `json` ra file, đừng serialize lại từ `config`.**
> Thư viện JSON của mỗi ngôn ngữ in số thực và sắp thứ tự khoá khác nhau. Ví dụ
> JavaScript in `51.0` thành `51`, Python in thành `51.0`. Trường `json` là đúng
> chuỗi mà giao diện web sinh ra — dùng nó thì file của bạn và file người dùng
> tự xuất từ web sẽ giống nhau từng byte.

---

## 4. Các endpoint còn lại

### `POST /validate`

Body là cấu hình JSON đã có. Chỉ kiểm tra luật.

```jsonc
{ "ok": false, "issues": ["Khoảng cách giữa hai view không được âm."],
  "stats": { "packages": 3, "totalSheets": 25, "requiredSheets": 20, "cadSheets": 11 } }
```

### `GET /template`

Trả về cấu hình mẫu đầy đủ: 3 bộ bản vẽ, 25 sheet. Dùng làm điểm xuất phát.

### `GET /health`

```json
{ "ok": true, "version": "0.1.0", "time": "2026-07-31T09:11:22.824Z" }
```

---

## 5. Mã trạng thái

| Mã | Nghĩa | Client nên làm gì |
|---|---|---|
| `200` | Hợp lệ | Lấy `json`, ghi ra file |
| `422` | Đọc được nhưng vi phạm luật | Hiện `issues` cho người dùng. **Không retry** |
| `400` | Không parse được, hoặc top-level không phải object | Báo file hỏng, đọc `error` |
| `413` | Body vượt 2 MB | Chặn từ phía client trước khi gửi |
| `503` | Server thiếu Node runtime | Lỗi hạ tầng — báo quản trị, retry sau |

Phân biệt cho đúng: `400` và `422` là **lỗi dữ liệu của người dùng**, retry vô
nghĩa. Chỉ `503` và lỗi mạng mới đáng retry.

Với `400` và `503`, body có dạng `{"ok": false, "error": "…"}`.

### Mẫu phản hồi `422` thật

```json
{
  "ok": false,
  "issues": [
    "ScaleMin phải nhỏ hơn hoặc bằng ScaleMax.",
    "Màu highlight phải có đúng 6 ký tự HEX.",
    "Key của các bộ bản vẽ phải là duy nhất.",
    "Bộ “Bộ bản vẽ 1” có sheet với Count nhỏ hơn 1."
  ],
  "stats": { "packages": 2, "totalSheets": 0, "requiredSheets": 0, "cadSheets": 0 }
}
```

`config` vẫn có trong phản hồi `422` để người dùng nhìn thấy dữ liệu đã chuẩn hoá
mà sửa.

---

## 6. Cạm bẫy quan trọng nhất: `warnings`

Mọi trường đều **tuỳ chọn**. Thiếu trường nào server tự bù mặc định. Tiện cho
giao diện web, **nguy hiểm khi gọi bằng máy**: gửi lên file gần như rỗng vẫn
nhận `200 OK` kèm cấu hình trông hoàn chỉnh — nhưng phần lớn là dữ liệu mẫu.

Gửi đúng một dòng `{"Workset":{"Name":"91.LINK CAD"}}` sẽ nhận:

```json
"warnings": [
  "Thiếu nhóm TitleBlock, đã dùng toàn bộ giá trị mặc định.",
  "Thiếu nhóm Keyplan, đã dùng toàn bộ giá trị mặc định.",
  "Thiếu nhóm Grid, đã dùng toàn bộ giá trị mặc định.",
  "PackageTypes thiếu hoặc không phải mảng, đã dùng 3 bộ bản vẽ mẫu của template."
]
```

Dòng cuối nguy hiểm nhất: **3 bộ bản vẽ hoàn toàn không phải của bạn** đã được
chèn vào file kết quả.

**Quy tắc:** hệ thống tự động luôn dùng `?strict=1`, hoặc kiểm `warnings` rỗng
trước khi ghi file. Chỉ để chế độ dễ dãi khi có người ngồi xem kết quả.

---

## 7. Danh mục thông báo

Dùng để hiển thị hoặc phân loại. **Đừng so khớp chuỗi chính xác** — nội dung có
thể đổi cách diễn đạt. Hãy dựa vào mã HTTP và việc mảng rỗng hay không.

### `issues` — 6 luật kiểm tra

| Luật | Thông báo |
|---|---|
| `ScaleMin` ≤ `ScaleMax` | `ScaleMin phải nhỏ hơn hoặc bằng ScaleMax.` |
| `HighlightColorHex` đúng 6 ký tự HEX | `Màu highlight phải có đúng 6 ký tự HEX.` |
| `ViewGapMm` không âm | `Khoảng cách giữa hai view không được âm.` |
| Có sheet `Cad` thì `Workset.Name` không rỗng | `Các sheet nguồn Cad cần Workset.Name để link CAD vào đúng workset.` |
| `Key` các bộ phải duy nhất | `Key của các bộ bản vẽ phải là duy nhất.` |
| `Key` không rỗng | `Bộ “<tên>” đang thiếu Key.` |
| Mọi sheet `Count` ≥ 1 | `Bộ “<tên>” có sheet với Count nhỏ hơn 1.` |

### `warnings` — các dạng có thể gặp

| Tình huống | Thông báo |
|---|---|
| Thiếu cả nhóm | `Thiếu nhóm <Nhóm>, đã dùng toàn bộ giá trị mặc định.` |
| Nhóm sai kiểu | `Nhóm <Nhóm> không phải object, đã dùng toàn bộ giá trị mặc định.` |
| Nhóm thiếu vài trường | `Nhóm <Nhóm> thiếu field: a, b, c.` |
| Thiếu `PackageTypes` | `PackageTypes thiếu hoặc không phải mảng, đã dùng 3 bộ bản vẽ mẫu của template.` |
| Phần tử bộ sai kiểu | `PackageTypes[i] không phải object, đã thay bằng bộ rỗng mặc định.` |
| Bộ thiếu `Key` | `PackageTypes[i] thiếu Key, đã đặt thành “Package1”.` |
| Bộ thiếu `DisplayName` | `PackageTypes[i] thiếu DisplayName, đã đặt thành “Bộ bản vẽ 1”.` |
| Bộ thiếu `ModelGroupPatterns` | `PackageTypes[i] thiếu ModelGroupPatterns, đã đặt thành mảng rỗng.` |
| Bộ thiếu `Sheets` | `PackageTypes[i] thiếu Sheets, đã đặt thành mảng rỗng.` |

---

## 8. Hợp đồng dữ liệu đầu vào

| Điều kiện | Chi tiết |
|---|---|
| Top-level | Phải là **object**. Mảng, số, chuỗi → `400` |
| Cú pháp | JSONC: `//`, `/* */`, dấu phẩy thừa đều chấp nhận |
| Mọi trường | Tuỳ chọn — thiếu thì bù mặc định và ghi vào `warnings` |
| Trường lạ | **Giữ nguyên**, đi thẳng ra output. Nhét metadata riêng vào thoải mái |
| Encoding | UTF-8. Tiếng Việt không bị escape thành `\uXXXX` |

7 nhóm cấu hình + 1 mảng bộ bản vẽ:

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

Mặc định khi thiếu: `DrawingType` → `"NewDrawing"`, `SourceType` → `"Blank"`,
`DisplayName` → `"Bản vẽ mới"`, `Count` → `1`, `IsRequired` → `true`.

---

## 9. Mã ví dụ

### C# — add-in Revit

```csharp
using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json;

public sealed class SheetConfigClient
{
    private static readonly HttpClient Http = new()
    {
        BaseAddress = new Uri("https://tranphuc120203-boc-tach-ban-ve.hf.space"),
        Timeout = TimeSpan.FromSeconds(90)   // Space ngủ thì request đầu chậm
    };

    /// <summary>Đọc file JSONC, trả về chuỗi JSON chuẩn để ghi ra đĩa.</summary>
    public static async Task<string> ChuanHoaAsync(string duongDanFile)
    {
        var noiDung = await File.ReadAllTextAsync(duongDanFile, Encoding.UTF8);
        return await ChuanHoaNoiDungAsync(noiDung);
    }

    public static async Task<string> ChuanHoaNoiDungAsync(string noiDung)
    {
        using var body = new StringContent(noiDung, Encoding.UTF8, "text/plain");
        using var res = await Http.PostAsync("/api/sheet-config/normalize?strict=1", body);

        var raw = await res.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(raw);
        var root = doc.RootElement;

        if (res.StatusCode == HttpStatusCode.UnprocessableEntity)
        {
            var loi = root.GetProperty("issues")
                          .EnumerateArray().Select(x => x.GetString());
            throw new SheetConfigInvalidException(string.Join("\n", loi));
        }

        if (!res.IsSuccessStatusCode)
        {
            var thongBao = root.TryGetProperty("error", out var e) ? e.GetString() : raw;
            throw new HttpRequestException($"HTTP {(int)res.StatusCode}: {thongBao}");
        }

        // Ghi thẳng chuỗi này, KHÔNG serialize lại từ "config".
        return root.GetProperty("json").GetString()!;
    }

    /// <summary>Đánh thức Space trước khi làm việc thật (tránh timeout lần đầu).</summary>
    public static async Task DanhThucAsync()
    {
        try { await Http.GetAsync("/api/sheet-config/health"); }
        catch { /* không sao, request thật sẽ thử lại */ }
    }
}

public class SheetConfigInvalidException : Exception
{
    public SheetConfigInvalidException(string message) : base(message) { }
}
```

Dùng:

```csharp
await SheetConfigClient.DanhThucAsync();
try
{
    var json = await SheetConfigClient.ChuanHoaAsync(@"C:\configs\DocumentSet.jsonc");
    File.WriteAllText(@"C:\configs\DocumentSet.json", json, new UTF8Encoding(false));
}
catch (SheetConfigInvalidException ex)
{
    TaskDialog.Show("Cấu hình sai", ex.Message);
}
```

### Python

```python
import requests

BASE = "https://tranphuc120203-boc-tach-ban-ve.hf.space"


class CauHinhSai(ValueError):
    """Dữ liệu người dùng sai — không retry."""


def chuan_hoa(noi_dung: str, strict: bool = True) -> str:
    r = requests.post(
        f"{BASE}/api/sheet-config/normalize",
        params={"strict": "1"} if strict else None,
        data=noi_dung.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        timeout=90,
    )
    d = r.json()

    if r.status_code in (400, 422):
        raise CauHinhSai("\n".join(d.get("issues") or [d.get("error", "")]))
    r.raise_for_status()
    return d["json"]


if __name__ == "__main__":
    with open("TEMPLATE_DocumentSetConfig.json", encoding="utf-8") as f:
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

    [IO.File]::WriteAllText(
        (Join-Path $PWD "DocumentSetConfig.json"), $res.json,
        (New-Object Text.UTF8Encoding $false))
    Write-Host "OK — $($res.stats.packages) bộ, $($res.stats.totalSheets) sheet"
}
catch {
    $loi = $_.ErrorDetails.Message | ConvertFrom-Json
    Write-Error ($loi.issues -join "`n")
}
```

### JavaScript / trình duyệt

```js
const BASE = "https://tranphuc120203-boc-tach-ban-ve.hf.space";

async function chuanHoa(noiDung) {
  const res = await fetch(`${BASE}/api/sheet-config/normalize?strict=1`, {
    method: "POST",
    headers: { "Content-Type": "text/plain" },
    body: noiDung,
  });
  const data = await res.json();

  if (res.status === 400 || res.status === 422) {
    throw new Error((data.issues ?? [data.error]).join("\n"));
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);

  return data.json;
}

// Từ <input type="file">
async function tuFile(file) {
  const json = await chuanHoa(await file.text());
  const url = URL.createObjectURL(new Blob([json], { type: "application/json" }));
  Object.assign(document.createElement("a"), {
    href: url, download: "DocumentSetConfig.json",
  }).click();
  URL.revokeObjectURL(url);
}
```

---

## 10. Vận hành

**Space ngủ sau 48 giờ không ai dùng.** Request đầu tiên sau khi ngủ mất khoảng
30 giây để container khởi động. Xử lý:

- Đặt timeout client tối thiểu **90 giây**.
- Gọi `GET /health` để đánh thức trước khi làm việc thật (xem `DanhThucAsync`).
- Retry `503` và lỗi mạng với backoff. **Không** retry `400`/`422`.

**Hiệu năng bình thường:** ~1 giây/request qua internet, đã gồm ~80ms khởi động
tiến trình Node phía server.

**Giới hạn:** body tối đa 2 MB. Không giới hạn tần suất, nhưng Space chạy CPU
chia sẻ — đừng bắn song song hàng loạt.

**Không có xác thực.** Ai biết URL đều gọi được. Dịch vụ không lưu gì nên không
rò rỉ dữ liệu cũ, nhưng nội dung bạn gửi lên **có đi qua máy chủ Hugging Face**.
Cân nhắc nếu cấu hình chứa thông tin dự án nhạy cảm.

---

## 11. Danh sách kiểm tra khi tích hợp

- [ ] Bật `?strict=1`, hoặc kiểm `warnings` rỗng trước khi ghi file
- [ ] Ghi thẳng trường `json`, không serialize lại từ `config`
- [ ] Timeout ≥ 90 giây
- [ ] Phân biệt `400`/`422` (lỗi người dùng, không retry) với `503`/lỗi mạng (retry được)
- [ ] Đọc và ghi file bằng UTF-8, không BOM
- [ ] Hiện `issues` nguyên văn cho người dùng — chúng đã viết sẵn bằng tiếng Việt dễ hiểu
- [ ] Gọi `/health` lúc khởi động ứng dụng để đánh thức Space

---

## 12. Khắc phục sự cố

| Hiện tượng | Nguyên nhân | Xử lý |
|---|---|---|
| Vào `/json-to-sheet` ra giao diện bóc tách | Cache trình duyệt cũ | Tải lại bỏ cache (`Ctrl+Shift+R` / `Cmd+Shift+R`) |
| Request đầu timeout | Space đang ngủ | Tăng timeout lên 90s, gọi `/health` trước |
| `503` kèm `"Không tìm thấy Node trong image"` | Dockerfile thiếu dòng copy binary node | Xem [backend/app/sheet_config/README.md](backend/app/sheet_config/README.md) |
| `400` với file mở được bằng Notepad | File có BOM, hoặc top-level không phải object | Ký tự đầu file phải là `{`. Lưu UTF-8 không BOM |
| Tiếng Việt thành `?????` | Client không gửi/đọc UTF-8 | Ép UTF-8 cả hai chiều |
| File kết quả khác bản web | Đã serialize lại từ `config` | Dùng thẳng chuỗi `json` |
| Nhận `200` nhưng nội dung lạ | Quên `strict=1`, server đã bù dữ liệu mẫu | Bật `strict=1` và đọc `warnings` |

---

## 13. Nguồn gốc mã

Logic nằm ở repo `json-to-sheet`, đóng gói thành
`backend/app/sheet_config/js/api-cli.mjs`. **Giao diện web và API này chạy chung
đúng một đoạn mã** — đã đối chiếu cho ra kết quả giống nhau từng byte trên file
template chuẩn (6686 byte, `sha256:8e209330aa089b6f…`).

Cách cập nhật logic và giao diện: xem
[backend/app/sheet_config/README.md](backend/app/sheet_config/README.md).
