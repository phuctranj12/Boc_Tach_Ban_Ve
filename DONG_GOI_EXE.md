# Đóng gói thành ứng dụng (.exe cho Windows)

Ứng dụng được gói thành **1 file thực thi**. Người nhận chỉ cần **double-click**:
server tự chạy → tự mở trình duyệt → dùng như bình thường. **Không cần cài Python/Node.**

> ⚠️ File `.exe` (Windows) **phải build trên máy Windows**. Máy Mac chỉ build được
> bản macOS. (PyInstaller chỉ tạo file cho đúng hệ điều hành đang chạy.)

---

## Cách 1 — Build .exe trên máy Windows (khuyến nghị)

Trên một máy **Windows** có sẵn:
- **Python 3.12 (64-bit)** — tải ở python.org, khi cài nhớ tick *"Add Python to PATH"*.
- **Node.js** (bản LTS) — tải ở nodejs.org.

Các bước:
1. Chép **cả thư mục dự án** này sang máy Windows.
   > ⚠️ Nếu nhận dưới dạng **file ZIP**: phải **Giải nén (Extract All)** ra một thư mục
   > thật *trước*, rồi double-click `build_windows.bat` trong thư mục đó. **Đừng** mở zip
   > rồi double-click file `.bat` ngay bên trong — khi đó Windows chỉ chạy mỗi file .bat ở
   > thư mục tạm, thiếu folder `backend`/`frontend` → build sẽ báo lỗi
   > *"No such file or directory: backend\requirements.txt"*.
2. Double-click **`build_windows.bat`** (hoặc chạy trong CMD). Cạnh nó phải thấy folder
   `backend` và `frontend`.
3. Chờ build xong (vài phút). File kết quả:
   ```
   backend\dist\MEP-Drawing-Reader.exe
   ```
4. Gửi **mỗi file `MEP-Drawing-Reader.exe`** đó cho người khác. Họ double-click là chạy.

---

## Trải nghiệm người nhận
- Double-click `.exe` → hiện 1 cửa sổ đen nhỏ (báo trạng thái) → trình duyệt tự mở giao diện.
- **Đừng đóng cửa sổ đen** khi đang dùng (đóng nó = tắt ứng dụng).
- Nếu trình duyệt không tự mở: xem link trong cửa sổ đen, hoặc mở file `MO_UNG_DUNG.txt`
  (tạo cạnh file .exe) rồi dán link vào trình duyệt.
- Dữ liệu (file PDF tải lên, kết quả) lưu trong thư mục **`data/`** nằm **cạnh file .exe**.

## Lưu ý
- File `.exe` khá nặng (~100–200MB) vì nhúng sẵn Python + thư viện đọc PDF. Bình thường.
- Lần mở đầu hơi chậm vài giây (giải nén nội bộ).
- Windows SmartScreen có thể cảnh báo "Unknown publisher" (do chưa mua chữ ký số):
  bấm **More info → Run anyway**. Đây là cảnh báo bình thường với .exe chưa ký.
- Ép cổng khác (nếu 8000 bận): đặt biến môi trường `PORT` trước khi chạy.

---

## Cách 2 — Build bản macOS (để TEST trên máy này)
```bash
./build_mac.sh
# Kết quả: backend/dist/MEP-Drawing-Reader  (double-click hoặc chạy ở Terminal)
```
Dùng để kiểm tra cơ chế chạy. **Không** dùng được trên Windows.

---

## File liên quan
| File | Vai trò |
|------|---------|
| `backend/run_app.py` | Điểm khởi chạy: bật server + tự mở trình duyệt |
| `backend/mep_reader.spec` | Cấu hình đóng gói PyInstaller (dùng chung Win/macOS) |
| `build_windows.bat` | Script build ra `.exe` trên Windows |
| `build_mac.sh` | Script build bản macOS để test |
