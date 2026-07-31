# Sheet Configure — module ở nhờ

Chuẩn hoá cấu hình bộ bản vẽ shop (`DocumentSetConfig`) từ JSON/JSONC sang JSON
hợp lệ. **Không liên quan gì tới luồng bóc tách bản vẽ** — ở chung image chỉ để
dùng một chỗ deploy duy nhất.

Ranh giới rất rõ: module này không import bất cứ thứ gì từ `app.core`, không
dùng chung `storage`, không ghi vào `data/`. Nó hoàn toàn stateless. Gỡ cả thư
mục này đi thì dự án bóc tách vẫn chạy nguyên vẹn, chỉ cần xoá thêm 2 dòng
`sheet_config` trong `app/main.py`.

## Endpoint

Tất cả nằm dưới prefix `/api/sheet-config`:

| Method | Path | Việc |
|---|---|---|
| `GET` | `/health` | Sức khoẻ + chẩn đoán Node |
| `GET` | `/template` | Cấu hình mẫu |
| `POST` | `/normalize` | JSONC thô → JSON chuẩn (`?strict=1`, `?pretty=0`) |
| `POST` | `/validate` | Chỉ kiểm tra luật |

Mã trạng thái: `200` hợp lệ · `422` đọc được nhưng vi phạm luật · `400` không
parse được · `413` body quá 2 MB · `503` thiếu Node hoặc gói JS.

## Vì sao gọi Node thay vì viết bằng Python

Logic gốc viết bằng TypeScript và **bản web chạy đúng đoạn code đó ngay trong
trình duyệt người dùng**. Viết lại sang Python nghĩa là từ đó có hai bản logic
phải giữ đồng bộ mãi mãi, mà chỉ cần lệch một chi tiết rất nhỏ là file cấu hình
xuất ra đã khác — ví dụ JavaScript in số `51.0` thành `51`, còn Python in thành
`51.0`.

Nên `runner.py` chỉ gọi tiến trình Node rồi chuyển tiếp nguyên trạng status và
body. Không có quyết định nghiệp vụ nào nằm ở phía Python.

Chi phí: mỗi request tốn thêm khoảng 80ms khởi động Node, và image nặng thêm
~110MB cho binary node. Với tần suất gọi của cấu hình bản vẽ thì không đáng kể.

## `js/api-cli.mjs` là file sinh tự động — đừng sửa tay

Nó được đóng gói từ repo `json-to-sheet`. Muốn cập nhật logic:

```bash
cd <đường-dẫn>/json-to-sheet/ui
npm run build:cli
cp dist-cli/api-cli.mjs <đường-dẫn>/git_Boc_Tach_Ban_Ve/backend/app/sheet_config/js/
```

Sửa trực tiếp vào file này thì lần build sau sẽ mất, và tệ hơn là bản web với
bản API sẽ cho ra kết quả khác nhau.

## Yêu cầu runtime

Cần có `node` trong `PATH`. Dockerfile lấy binary từ stage `frontend`
(`node:20-slim`) sang runtime `python:3.12-slim` — cùng nền Debian bookworm nên
chạy trực tiếp, không cần cài thêm thư viện hệ thống.

Chạy local mà máy chưa có Node thì `/api/sheet-config/health` trả `503` kèm
đường dẫn nó đang tìm, các endpoint khác cũng vậy. Luồng bóc tách không bị ảnh
hưởng.
