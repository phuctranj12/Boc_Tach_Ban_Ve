# Bảng phân loại "Tong hop type.dwg" — có bao nhiêu LOẠI sơ đồ?

> Kết quả Phase 2 (Discovery) của kế hoạch. Khảo sát thực hiện trên dữ liệu **vector**
> của `Tong hop type.dwg` (chuyển DWG→DXF bằng ODA, đọc bằng `ezdxf`). Đây là bản
> **sơ bộ để bạn xác nhận**; bản chốt chính xác từng tủ sẽ chạy trên **PDF** (pipeline
> chính theo lựa chọn của bạn). Số liệu chi tiết: [extracted_json/template_report.json](extracted_json/template_report.json).

## TL;DR — trả lời trực tiếp câu hỏi

- File có **28 sheet** ("SINGLE LINE DIAGRAM 1→28") = 28 "type" do kỹ sư đánh số.
- Nhưng về **cấu trúc để code**, KHÔNG phải 28 cái khác nhau. Tất cả thuộc **MỘT họ cáp
  MỚI** và **~2 họ cấu trúc**. ⇒ **Code chỉ cần ~1 extractor family mới**, đúng kiểu
  registry hiện tại. **"Code theo từng loại" hoàn toàn ổn và không bùng nổ số lượng.**

## 1. Họ ký hiệu cáp — quyết định nhất

| Họ cáp | Ví dụ | Số nhãn trong file | Extractor xử lý |
|---|---|---|---|
| A — busbar + vạch chéo | `2x1C 2.5mm2 Cu/PVC` | **0** | `busbar_slash` (đã có) |
| B — ma trận | `CU/PVC 2X(1X2.5MM2)` | **0** | `panel_table` (đã có) |
| **C — khách sạn** | `2 x 16 mmSQ Cu/PVC + E 16 mmSQ` | **554** | ❌ **CHƯA có → cần làm** |

➡️ Cả bộ dùng **100% họ C** — khác hẳn 2 loại đã code. Trong họ C có 2 biến thể đơn vị:
**`mmSQ`** (826 lần) và **`mm2`** (103 lần) → parser tiết diện phải nhận cả hai.

## 2. Họ cấu trúc (gom theo nội dung) — ~2 loại + sheet đặc biệt

| Họ cấu trúc | Đặc điểm | Tủ tiêu biểu | Quy mô |
|---|---|---|---|
| **Tủ phòng (guestroom_db)** | Gọn, đồng nhất cao; có loại phòng GR.KING/TWIN/PRE; 1 MCB tổng + ít lộ | `DB-14F-MH-GR1..7` | **~179 tủ** (đa số) |
| **Tủ khu chung (common_db)** | Nhiều lộ hơn; khu kỹ thuật/dịch vụ | `...-MH-COM/KIT/LIFT/OFF/BOH/HW/SER` | ~60 tủ |
| **Sheet đặc biệt** | Riser/schedule, **không có cáp theo lộ** | (2 sheet) | có thể ngoài phạm vi takeoff |

- Loại phòng guestroom: **KING 76 · TWIN 73 · PRE 2** — chúng **cùng một template thị
  giác**, chỉ khác tải bên trong ⇒ **1 extractor** lo được cả 3.
- Hậu tố chức năng tủ thường gặp: GR 179, COM 30, KIT 6, LIFT 5, OFF 4, BOH 4, HW 3…

## 3. Định dạng phụ (để thiết kế parser)

- **CB đầu lộ** rất đều: `32A 1P MCB 10 kA`, `16A 2P RCCB 30 mA`, `16A 1P MCB 4.5 kA`…
  → mẫu `{dòng}A {cực}P {loại} {kA|mA}` (khác cách ghi của Kiểu B `MCB 3P 32A 6kA`).
- **Đi dây/chứa**: cáp tray/trunking **489** vs ống ỐNG/PVC **291** → cần trường phân biệt
  máng cáp (TRAY/TRUNKING) với ống luồn.
- Tải guestroom có công suất dạng `[2.4/ 5.4 kW]`.

## 4. Vì sao kết luận "1 template lặp lại" đáng tin

1. Cùng 1 bộ block ký hiệu (`ELEC0342`, `FUSE`…), mỗi block lặp ~1 lần/sơ đồ trên 28 sheet.
2. 100% cáp cùng họ C; CB cùng một văn phong; cùng cách ghi công suất `kW`.
3. 28 sheet là 28 *paperspace layout* xếp lưới đều — bố cục chuẩn hoá.

## 5. Hệ quả cho việc code — ĐÃ LÀM & TEST ✅

Đã thêm extractor họ C và test trên **554 mẫu cáp thật** từ chính file DWG (qua DXF):
- **`backend/app/core/takeoff/hotel_db.py`** — `detect_score` + `extract` + lõi
  `extract_items(tokens)` **tách rời nguồn** (chạy được cả PDF lẫn nguồn khác). Đã đăng
  ký vào `EXTRACTORS`.
- Parser họ C (chạy đúng 100% trên dữ liệu thật):
  - **Cáp**: `2 x 16 mmSQ Cu/PVC + E 16 mmSQ ON TRAY/TRUNKING` → `size=16mm2`, lõi=2,
    đất=16mm2, chống_cháy (Mica/LSHF/XLPE), containment (máng/ống).
  - **CB**: `32A 1P MCB 10 kA` → `MCB 1P 32A 10kA`; `16A 2P RCCB 30 mA` → `RCCB 2P 16A 30mA`.
  - **Công suất**: `[2.4/ 5.4 kW]` → `2.4/5.4 kW`; bỏ placeholder `( ** kW )`.
- Kết quả test: bóc **554 lộ**, đủ trường `size=554/554, cb=554, power=551, conduit=451`.
  Mẫu JSON: [extracted_json/hotel_db.sample_takeoff.json](extracted_json/hotel_db.sample_takeoff.json).
- **Không hồi quy**: `detect_score(hotel_db)` = 0 trên cả 2 file cũ (busbar A / panel B);
  2 file cũ vẫn ra đúng loại.

**Còn lại (cần PDF dự án thật):** phần *gán lộ về đúng tủ* (segmentation từng sơ đồ) hiện
dùng "gần nhất" nên còn nhiễu trên file CATALOG. Trên PDF SLD dự án thật (mỗi tủ 1 sơ đồ
đầy đủ) sẽ tách vùng sạch hơn (Phase 1). Nếu common_db khác cấu trúc nhiều → thêm
`common_db.py`; chi phí tuyến tính, không phá kiến trúc.

> ⚠️ Lưu ý quan trọng: `Tong hop type.dwg` là **CATALOG "type" rút gọn** (~2,3 cáp/sơ đồ,
> chủ yếu cáp nguồn vào). **Takeoff đầy đủ từng lộ phải lấy từ bộ SLD dự án thật** (các
> bản LCP/CCP được tham chiếu xref), không có trong file tổng hợp này.

## 6. Việc cần bạn làm tiếp (Phase 0)

Xuất **PDF** từ `Tong hop type.dwg` (in/plot mỗi layout 1 trang, hoặc cả tập). Đặt vào
thư mục dự án. Khi có PDF, mình sẽ: chốt phân loại chính xác từng tủ + viết extractor họ C
+ kiểm thử BOQ.

> Ghi chú: số đếm ở trên lấy từ text vector DXF (một phần text nằm trong block/attrib/xref
> nên con số *tuyệt đối* có thể nhỉnh/thiếu chút ít, nhưng **tỉ lệ và kết luận họ loại là
> chắc chắn**). Bản trên PDF sẽ cho con số từng-tủ chính xác.
