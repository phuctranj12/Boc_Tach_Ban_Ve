> **Gửi Claude:** Hãy đọc kỹ toàn bộ brief này rồi viết cho tôi một **tài liệu giới thiệu**
> hoàn chỉnh theo yêu cầu ở [Phần 9](#9-yêu-cầu-đầu-ra-cho-claude). Mọi số liệu, tên layer,
> ví dụ trong brief đều là **dữ liệu thật** — hãy dùng đúng, đừng bịa thêm con số.

---

## 0. Vai trò & mục tiêu

Bạn là một người viết kỹ thuật giỏi kể chuyện. Nhiệm vụ: biến một phương pháp kỹ thuật
"khó nhằn" thành một tài liệu **dễ hiểu, hấp dẫn, truyền cảm hứng** cho:

- **Kỹ sư MEP / QS / chủ nhiệm dự án** — không biết lập trình.
- **Lãnh đạo / người ra quyết định** — cần thấy tiềm năng để đầu tư mở rộng.

Tài liệu phải làm được 3 việc: (1) giải thích **cách hệ thống "đọc" bản vẽ**, (2) chứng minh
bằng **ví dụ thật** rằng nó chạy được, (3) mở ra **nhiều hướng phát triển** trong tương lai.

---

## 1. Bối cảnh & bài toán

Kỹ sư điện/MEP hằng ngày phải **bóc tách khối lượng** (đếm ổ cắm, đèn, đo mét cáp, liệt kê
ống luồn…) từ bản vẽ để lập dự toán (BOQ). Việc này làm **thủ công**, tốn hàng giờ, dễ sai
sót, và phải lặp lại mỗi khi bản vẽ thay đổi.

Bản vẽ thường được giao dưới dạng **PDF xuất ra từ AutoCAD**. Nhiều người nghĩ PDF chỉ là
"tờ giấy ảnh" — muốn máy hiểu thì phải chụp lại, dùng AI nhìn ảnh (OCR/Vision) để đoán.
**Cách đó chậm, đắt, và hay đoán sai.**

Dự án này chọn một **cách tiếp cận mới**: PDF xuất từ AutoCAD **không phải ảnh** — bên trong
nó vẫn còn **dữ liệu vector thật** (từng đường nét, từng chữ, đều có toạ độ chính xác và tên
lớp/layer). Ta đọc thẳng dữ liệu đó ra, **không cần AI nhìn ảnh, không OCR**.

> **Trạng thái hiện tại:** hệ thống đang đọc được **sơ đồ nguyên lý (single-line diagram)
> của hệ điện & tủ điện**, và tự động **trích ra từng lộ** (mỗi aptomat cấp cho tải nào,
> dùng cáp gì, ống gì). Đây mới là bước đầu — nền tảng này còn mở rộng được rất xa.

---

## 2. Ý tưởng cốt lõi (giải thích cho người không biết code)

Hãy tưởng tượng bản vẽ PDF như một **bàn cờ trong suốt**:

- Mỗi **chữ/số** (ví dụ `DB-2BR-3`, `2P-63A`, `2.5mm2`) là một quân cờ, và ta biết chính xác
  nó **nằm ở toạ độ nào**.
- Mỗi **nét vẽ** (đường dây, hình chữ nhật, vạch chéo) cũng có toạ độ hai đầu, và quan trọng
  nhất: **nó thuộc lớp (layer) nào** — ví dụ layer `E-PO WIRING` (dây động lực),
  `A-LIGHT` (đèn), `A-WALL` (tường)…

Vì mọi thứ có **toạ độ + tên layer**, máy có thể suy luận như một kỹ sư:
*"Chữ `2P-63A` này nằm ngay cạnh nét dây trên layer điện, phía dưới có chữ tên lộ `P1`…
→ đây là aptomat 2 pha 63A của lộ P1."*

**Điểm mấu chốt cần nhấn mạnh trong tài liệu:** đây **không phải** máy nhìn ảnh rồi đoán.
Đây là máy **đọc đúng dữ liệu gốc** mà người vẽ đã tạo ra trong AutoCAD → độ chính xác cao,
tốc độ nhanh, và **giải thích được vì sao ra kết quả đó** (truy vết được).

### Một lưu ý kỹ thuật quan trọng: "block" biến mất
Trong AutoCAD, một ký hiệu (ổ cắm, đèn…) là một **block** dùng đi dùng lại. Nhưng khi xuất
ra PDF, **block bị "nổ" (explode) thành các nét rời rạc** — PDF không lưu khái niệm block.
Cái **duy nhất còn sót lại** để nhận dạng là **tên layer**. Vì vậy hệ thống nhận diện lại
mọi thứ **theo hình học + layer**, chứ không thể hỏi "cho tôi tất cả block ổ cắm".

---

## 3. Nguyên liệu thô — chính xác máy nhìn thấy gì

Công cụ đọc PDF (thư viện PyMuPDF) trả về **2 loại dữ liệu, đều có toạ độ** (đơn vị *point*;
khổ A3 ≈ **2384 × 1684** point):

**a) Chữ (words)** — mỗi từ kèm toạ độ. Ví dụ thật từ trang bìa một căn hộ 2 phòng ngủ:

| Chữ | Ý nghĩa | Toạ độ (x, y) |
|---|---|---|
| `DB-2BR-3` | Tên tủ điện căn hộ | (729, 197) |
| `DB-2BR-3/P1` | Tên **lộ** P1 của tủ | (638, 261) |
| `MCB 2P-63A 6kA` | Aptomat 2 pha 63A | (680, 1030) |
| `BUSBAR 63A` | Thanh cái 63A | (449, 1066) |
| `WP`, `WH`, `TV`, `AC`, `REF` | Ký hiệu tải (ổ chống nước, bình nóng lạnh, TV, điều hoà, tủ lạnh) | rải rác |

**b) Nét vẽ (drawings)** — mỗi nét là line / hình chữ nhật / cung, kèm **layer**. Ví dụ thật
số lượng nét theo layer ở **một trang**:

| Layer | Số nét | Là gì | Dùng cho bóc điện? |
|---|---:|---|:---:|
| `I-FURN` | 12.918 | Nội thất | ❌ bỏ |
| `A-WALL` | 5.163 | Tường | ❌ bỏ |
| `S-COLS` | 4.446 | Cột | ❌ bỏ |
| `E-PO WIRING` | 1.082 | **Dây động lực** | ✅ |
| `E-Line` | 130 | **Dây/tuyến điện** | ✅ |
| `A-LIGHT` | 120 | **Đèn** | ✅ |
| `E-SW-2WAY` | 21 | **Công tắc 2 chiều** | ✅ |

> Con số biết nói: một trang có tới **~91.000 nét vẽ**, nhưng đa số là tường/cột/nội thất.
> Toàn bộ 14 trang có ~1,36 **triệu** nét "trang trí" bị **loại bỏ**, chỉ giữ lại
> **~50.000 nét thật sự liên quan đến điện**. Đây là bước "gạn đục khơi trong" đầu tiên.

---

## 4. Cơ chế suy luận — 3 bước

**Bước 1 — Lọc theo layer.** Chỉ giữ các nét thuộc nhóm điện: dây (`wire`), công tắc
(`switch`), đèn (`light`), ổ cắm (`socket`), thiết bị (`equipment`), chữ (`text`). Mọi thứ
khác gắn nhãn `other` và **vứt đi**. → giảm nhiễu khổng lồ.

**Bước 2 — Ghép chữ với hình học theo toạ độ.** Máy tìm các chữ nằm **gần** một nét dây/thiết
bị để gán ý nghĩa: tên tủ, tên lộ, thông số aptomat, tên tải… (như ví dụ ở Phần 3).

**Bước 3 — Đếm "vạch chéo" để suy ra cáp.** Trên sơ đồ nguyên lý, số lõi của một sợi cáp được
vẽ bằng những **vạch chéo `/`** cắt qua đường dây. Máy **đếm số vạch chéo** trên layer dây →
suy ra số lõi → ghép với thông số ghi kèm (dạng `2x1C 2.5mm2 Cu/PVC`) để ra **đúng quy cách
cáp và ống luồn**. (Cơ chế này đã kiểm chứng khớp 100% trên bản vẽ mẫu.)

> Có thể mô tả hình ảnh: một đường ngang là "sợi cáp", ba gạch chéo `/// ` trên nó nghĩa là
> "3 lõi". Máy đếm gạch thay cho mắt người.

---

## 5. Ví dụ chạy thật — từ nét vẽ đến dòng dự toán

Lấy **lộ L1** của tủ `DB-2BR` làm ví dụ. Từ các mảnh rời trên bản vẽ (tên lộ + vạch chéo +
thông số + ký hiệu ống), hệ thống ghép lại thành **một dòng BOQ hoàn chỉnh**:

```json
{
  "panelName": "DB-2BR",
  "roadName":  "L1",
  "loadName":  "QUẠT HÚT TOILET",
  "cableSpec": "2x1C 2.5mm2 Cu/PVC + 1C-2.5mm2 Cu/PVC (E)",
  "conduit":   "ỐNG PVC D20"
}
```

Nghĩa là: *"Lộ L1 của tủ DB-2BR cấp cho **quạt hút toilet**, dùng cáp đồng bọc PVC 2.5mm²
(2 lõi pha + 1 lõi tiếp địa), luồn trong **ống PVC D20**."* — tất cả **tự động**, từ một
tờ PDF.

---

## 6. Kết quả & hai "bộ não" song song

Hệ thống xuất ra 2 loại kết quả từ **cùng một nguồn vector**:

1. **Bản đồ quan hệ (Knowledge Graph)** — trả lời *"thiết bị nào nối/điều khiển/cấp nguồn cho
   thiết bị nào"* (công tắc này bật đèn nào, MCB này cấp cho ổ cắm nào).
2. **Bảng khối lượng (Takeoff / BOQ)** — trả lời *"cần bao nhiêu, loại gì"* (mét cáp, số ống,
   quy cách), xuất thẳng ra **Excel**.

---

## 7. Vì sao cách này mạnh — và giới hạn hiện tại

**Ưu điểm (nên làm nổi bật):**
- **Chính xác**: đọc đúng dữ liệu gốc kỹ sư đã vẽ, không "đoán" như nhìn ảnh.
- **Nhanh & rẻ**: không cần GPU/OCR/AI vision; chạy được trên máy thường.
- **Giải thích được**: mỗi kết quả truy vết ngược về nét vẽ/toạ độ cụ thể → tin cậy, dễ kiểm.
- **Không phụ thuộc chất lượng ảnh**: không sợ mờ, nghiêng, scan xấu.

**Giới hạn hiện tại (thành thật để mở đường phát triển):**
- Chỉ chạy trên PDF **vector** xuất từ CAD (PDF scan/ảnh thì không có dữ liệu này).
- Phụ thuộc **quy ước layer** của đơn vị vẽ; layer đặt lộn xộn thì phải hiệu chỉnh.
- Mới đọc **sơ đồ nguyên lý điện**; chưa đo chiều dài thực trên mặt bằng, chưa sang hệ khác.

---

## 8. Hướng phát triển tương lai (gợi ý để Claude mở rộng thành phần hấp dẫn nhất)

Hãy trình bày phần này như những **cánh cửa đang mở**, khơi gợi trí tưởng tượng:

- **Đọc mặt bằng để đo chiều dài cáp thật**: dùng chính con số kích thước trên bản vẽ làm
  thước tỉ lệ → tự tính mét dây theo đường đi thực, không cần bóc tay.
- **Mở sang các hệ MEP khác**: cấp thoát nước, điều hoà (HVAC), phòng cháy (PCCC), thang
  máng cáp — cùng một nguyên lý "vector + layer".
- **Đếm ký hiệu tự động**: nhận dạng lại ổ cắm/đèn/công tắc theo hình học để **đếm số lượng**.
- **Đối chiếu chéo**: so sơ đồ nguyên lý với mặt bằng để **tự phát hiện thiếu/lệch** thiết kế.
- **Tự lập BOQ + đơn giá**: từ khối lượng ra bảng dự toán có tiền, xuất Excel.
- **Ngân hàng tri thức cáp/thiết bị**: học quy cách theo từng dự án/khách hàng để bóc nhanh hơn.
- **Công cụ web + xử lý hàng loạt**: kéo-thả nhiều PDF, bóc cả bộ hồ sơ trong vài phút.
- **Chiều ngược lại**: từ BOQ/dữ liệu → kiểm tra hoặc dựng lại bản vẽ.

---

## 9. Yêu cầu đầu ra cho Claude

Hãy viết **một tài liệu Markdown hoàn chỉnh** với các đặc điểm:

- **Ngôn ngữ:** tiếng Việt, giọng kể chuyện, ấm áp, tránh thuật ngữ code; thuật ngữ kỹ thuật
  nào bắt buộc thì giải thích bằng ví dụ/ẩn dụ đời thường.
- **Đối tượng:** kỹ sư & lãnh đạo **không biết lập trình**.
- **Cấu trúc gợi ý:** (1) mở đầu bằng "nỗi đau" bóc tách thủ công → (2) "khoảnh khắc aha":
  PDF không phải ảnh mà là dữ liệu sống → (3) cách máy đọc (dùng ẩn dụ bàn cờ/bản đồ) →
  (4) ví dụ thật chạy được (dùng lộ L1 ở Phần 5) → (5) vì sao đáng tin → (6) **tương lai
  mở ra những gì** (phần dài, truyền cảm hứng) → (7) kết luận thôi thúc hành động.
- **Trực quan:** thêm sơ đồ ASCII đơn giản, bảng, và các "hộp ví dụ" để dễ đọc.
- **Độ dài:** đủ chi tiết để thuyết phục (khoảng 1.500–2.500 từ), nhưng chia mục rõ, đọc lướt
  được.
- **Cảm xúc chủ đạo:** "Hoá ra máy có thể đọc bản vẽ *đúng như kỹ sư đọc* — và đây mới chỉ là
  khởi đầu."
- Dùng đúng các số liệu/ví dụ thật trong brief này; **không bịa** thông số kỹ thuật mới.
