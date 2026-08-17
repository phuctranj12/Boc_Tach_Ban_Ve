# Deploy lên cloud để nhiều người test

Mục tiêu: có **1 link HTTPS cố định** cho mọi người vào dùng thử, luôn chạy, không
phụ thuộc máy cá nhân. App đóng gói thành **1 container Docker** chạy cả API lẫn giao
diện (same-origin), nên deploy ở đâu cũng được.

**Khuyến nghị: Hugging Face Spaces (Docker) — miễn phí, RAM 16GB** (mục 2 bên dưới),
hợp app này vì xử lý PDF tốn bộ nhớ. Render (mục 3) là lựa chọn thay thế.

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

> Muốn giống hệt môi trường HF (chạy bằng user không phải root): thêm `--user 1000`
> vào lệnh `docker run`.

---

## 2. Deploy lên Hugging Face Spaces (Docker) — MIỄN PHÍ, khuyến nghị

Free, RAM tới **16GB** (đủ cho PDF lớn). Space sẽ có link dạng
`https://<user>-boc-tach-ban-ve.hf.space`. Ngủ khi lâu không ai dùng, vào lại tự thức.

Repo đã cấu hình sẵn cho HF:
- `README.md` có khối `---` khai báo `sdk: docker` và `app_port: 8000`.
- `Dockerfile` chạy bằng user `UID 1000` (đúng chuẩn HF) và cấp quyền ghi `data/`.

### Các bước

1. Có tài khoản <https://huggingface.co> (miễn phí).
2. Tạo Space: **New → Space** → đặt tên (vd `Boc_Tach_Ban_Ve`) →
   **SDK = Docker** (chọn *Blank*) → **Hardware = CPU basic (free)** → Create.
3. HF hiện hướng dẫn git. Lấy mã nguồn lên Space bằng 1 trong 2 cách:

   **Cách A — thêm remote HF vào repo hiện tại rồi push:**
   ```bash
   # cần "Access Token" (Settings → Access Tokens, quyền write) để đăng nhập khi push
   git remote add hf https://huggingface.co/spaces/<user>/<ten-space>
   git push hf main
   ```
   > Khi push hỏi mật khẩu: dán **Access Token** (không phải mật khẩu tài khoản).

   **Cách B — clone Space rồi copy code vào** (nếu muốn tách khỏi repo GitHub):
   ```bash
   git clone https://huggingface.co/spaces/<user>/<ten-space> hf-space
   # copy toàn bộ file dự án vào hf-space/ (trừ .git), rồi:
   cd hf-space && git add . && git commit -m "deploy" && git push
   ```
4. Vào tab **App** của Space, chờ HF build (vài phút, xem log ở tab **Logs**). Xong là
   có link công khai để chia sẻ cho mọi người test.

> **Lưu ý HF:** dữ liệu upload là **tạm** (mất khi Space restart/build lại). Muốn giữ
> bền cần bật *Persistent Storage* (tính phí). Với mục đích test thì để tạm là được.

---

## 3. Deploy lên Render (thay thế)

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

## 4. Lưu ý vận hành (quan trọng)

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

## 5. Các file liên quan

| File | Vai trò |
|------|---------|
| `Dockerfile` | Build giao diện + đóng gói backend chạy chung 1 container (user UID 1000 cho HF) |
| `.dockerignore` | Loại venv/node_modules/data/pdf khỏi build cho nhẹ & nhanh |
| `README.md` | Khối `---` đầu file = cấu hình Hugging Face Space (sdk: docker, app_port) |
| `render.yaml` | Cấu hình deploy Render (Blueprint) — lựa chọn thay thế |
| `backend/app/main.py` | FastAPI phục vụ cả API (`/api/...`) lẫn giao diện tĩnh |
