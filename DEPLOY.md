# Deploy lên cloud để nhiều người test

Mục tiêu: có **1 link HTTPS cố định** cho mọi người vào dùng thử, luôn chạy, không
phụ thuộc máy cá nhân. App đóng gói thành **1 container Docker** chạy cả API lẫn giao
diện (same-origin), nên deploy ở đâu cũng được. Dưới đây hướng dẫn **Render** (đơn giản
nhất), kèm cách chạy Docker cục bộ để kiểm thử trước.

---

## 1. Kiểm thử cục bộ (nên làm trước khi deploy)

Cần cài **Docker Desktop**. Tại thư mục dự án:

```bash
docker build -t mep-reader .
docker run --rm -p 8000:8000 -e PORT=8000 mep-reader
```

Mở trình duyệt: <http://localhost:8000>

- Kiểm tra sức khoẻ: <http://localhost:8000/api/health> → `{"status":"ok",...}`
- Upload thử 1 file PDF → vào **Duyệt & Xuất BOQ** → xuất Excel/JSON.

Dừng: `Ctrl+C`.

---

## 2. Deploy lên Render (khuyến nghị)

Có sẵn file `render.yaml` (Blueprint) nên chỉ vài bước bấm chuột.

1. **Đưa mã nguồn lên GitHub** (repo private cũng được):
   ```bash
   git add .
   git commit -m "Thêm cấu hình deploy Docker + Render"
   git push
   ```
2. Vào <https://dashboard.render.com> → **New +** → **Blueprint**.
3. Kết nối GitHub, chọn repo này → Render tự đọc `render.yaml` → **Apply**.
4. Chờ build (lần đầu vài phút). Xong sẽ có URL dạng
   `https://mep-drawing-reader.onrender.com` → **chia sẻ link này** cho người cần test.
5. Mỗi lần `git push`, Render tự build lại (autoDeploy).

> **Gói máy:** `render.yaml` đặt `plan: standard` (≈2GB RAM). Xử lý PDF lớn tốn bộ nhớ;
> gói free 512MB dễ bị kill giữa chừng. Có thể chỉnh `plan`/`region` trong `render.yaml`.

### Nền tảng khác (tuỳ chọn)
Cùng `Dockerfile` này chạy được nơi khác không cần đổi:
- **Railway** (<https://railway.app>): New Project → Deploy from GitHub → tự nhận Dockerfile.
  Nhớ đặt RAM ≥ 2GB trong Settings.
- **Fly.io**: `fly launch` (tự dùng Dockerfile) → `fly deploy`.

---

## 3. Lưu ý vận hành (quan trọng)

- **RAM ≥ 2GB.** PDF lớn + render ảnh preview + bóc trước tất cả trang (chạy nền) rất tốn
  bộ nhớ. Instance nhỏ sẽ bị hệ thống kill → lỗi 502.
- **PDF rất lớn có thể timeout.** `/analyze` đọc cả file vào RAM rồi phân tích **đồng bộ**
  trước khi trả kết quả; file quá lớn có thể chạm giới hạn thời gian request của nền tảng.
  Chấp nhận cho giai đoạn test; nếu gặp nhiều thì cần tách phân tích thành job nền (việc sau).
- **Dữ liệu là tạm thời.** Không gắn đĩa → job đã upload **mất khi restart/redeploy**. Với mục
  đích test là ổn. Muốn giữ lại: bỏ comment khối `disk:` trong `render.yaml` (mount
  `/app/backend/data`).
- **Link mở hoàn toàn — không có mật khẩu.** Ai có link đều upload/xử lý được. Chỉ chia sẻ
  trong nhóm cần test. Muốn khoá lại có thể thêm mật khẩu sau.

---

## 4. Các file liên quan

| File | Vai trò |
|------|---------|
| `Dockerfile` | Build giao diện + đóng gói backend chạy chung 1 container |
| `.dockerignore` | Loại venv/node_modules/data/pdf khỏi build cho nhẹ & nhanh |
| `render.yaml` | Cấu hình deploy Render (Blueprint) |
| `backend/app/main.py` | FastAPI phục vụ cả API (`/api/...`) lẫn giao diện tĩnh |
