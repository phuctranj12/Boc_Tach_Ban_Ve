# boc-tach-ban-ve

Bóc tách bản vẽ MEP (PDF) của HAWEE: nhận diện đối tượng, dựng đồ thị quan hệ
điều khiển/cấp nguồn, xuất BOQ. Kèm API server (FastAPI) và MCP server cho Claude.

## Cài đặt

```bash
pip install boc-tach-ban-ve
```

## Dùng như thư viện

```python
from boc_tach_ban_ve import analyze_pdf, answer

result = analyze_pdf("ban_ve.pdf")
print(result.stats)
print(answer(result, "DB-1 cấp nguồn cho những gì?"))
```

Mount API vào ứng dụng FastAPI khác:

```python
from boc_tach_ban_ve import create_app
main_app.mount("/boc-tach", create_app())
```

## Dòng lệnh

```bash
boc-tach-ban-ve analyze ban_ve.pdf -o ket_qua.json
boc-tach-ban-ve serve --port 8001     # API: /docs, MCP: /mcp
```

## Biến môi trường

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `BOC_TACH_HOME` | Thư mục ghi `data/` (upload, kết quả) | `~/.boc_tach_ban_ve` |
| `BOC_TACH_FRONTEND_DIST` | Thư mục giao diện đã build để server phục vụ | không có (chỉ API) |

Nhóm chức năng Sheet Configure (`/api/sheet-config`, tool MCP `*_sheet_config`)
cần **Node.js** có trong PATH. Các chức năng bóc tách không cần.
