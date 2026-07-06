# Tool suy luận thế nào? — Giải thích bằng VÍ DỤ THẬT

> Tài liệu này KHÔNG nói lý thuyết. Nó lấy **đúng dữ liệu thật** trong
> [extracted_json/](extracted_json/) và đi **từng bước** để bạn thấy:
> *thực thể này là gì → liên kết với cái gì → nhờ logic nào suy ra → ra JSON nào.*
>
> Bản kỹ thuật đầy đủ: [LOGIC_BOC_TACH.md](LOGIC_BOC_TACH.md).

---

## Ý tưởng cốt lõi (đọc 30 giây)

Tool **không hiểu hình vẽ**. Nó chỉ thấy 2 thứ, **đều có toạ độ (x, y)**:

1. **Chữ** — ví dụ `"CHIẾU SÁNG"` ở vị trí (x=491, y=1394).
2. **Nét vẽ** — ví dụ một đoạn thẳng từ (356,1267) đến (492,1267).

Vậy làm sao biết "đèn này nối với cáp kia"? → **Dựa vào VỊ TRÍ**:
ai **thẳng hàng** với ai, ai **bị đánh dấu** bằng vạch chéo, ai **nối bằng đường dây**.
Đó là toàn bộ "trí tuệ" của tool. Dưới đây là 3 ví dụ cụ thể.

> **Đọc mục BƯỚC 0 trước.** 3 ví dụ phía dưới trả lời "tải này ăn cáp nào".
> Nhưng trước đó tool phải làm 2 việc nền tảng mà người ta hay quên hỏi:
> **(0A) khoanh vùng nào trên trang là sơ đồ** và **(0B) đâu là MỘT lộ.**
> Thiếu 2 bước này thì 3 ví dụ dưới vô nghĩa.

---

## TOÀN CẢNH LUỒNG (đọc cái này là nắm 80%)

Mọi trang sơ đồ đều đi qua đúng 5 chặng. 3 ví dụ trong tài liệu chỉ là chặng ④.

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  ① TRANG PDF                                                           │
  │     get_text("words"/"dict") → chữ (x,y), ngang/dọc                     │
  │     get_drawings()           → nét vẽ (đoạn thẳng)                      │
  └───────────────────────────────┬──────────────────────────────────────┘
                                   ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  ② CHỌN KIỂU SƠ ĐỒ  (detect_score)                                     │
  │     đếm cột "2x1C" → điểm Kiểu A   |   đếm số mạch có cáp thẳng cột →   │
  │     điểm Kiểu B.  Ai điểm cao hơn thì dùng extractor đó.                │
  │     (ban_ve_goc: A=4,B=0 → Kiểu A) (loai_2: A=0,B=75 → Kiểu B)          │
  └───────────────────────────────┬──────────────────────────────────────┘
                                   ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  ③ BƯỚC 0 — KHOANH VÙNG + PHÁT HIỆN LỘ      ◄── chặng hay bị bỏ quên   │
  │     Kiểu A: khoanh vùng SLD → đếm cột tải dọc   = danh sách lộ          │
  │     Kiểu B: bắt mọi số mạch (regex)             = danh sách lộ          │
  │     Kết quả: "trang này có N lộ, mỗi lộ có 1 trục x"                    │
  └───────────────────────────────┬──────────────────────────────────────┘
                                   ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  ④ VỚI MỖI LỘ → GẮN CÁP/ỐNG/TẢI   ◄── chính là VÍ DỤ 1, 2, 3           │
  │     Kiểu A: vạch chéo "/" trùng trục x → cáp   (Ví dụ 1)               │
  │     Kiểu B: chữ dọc thẳng cùng trục x → cáp/ống/tải (Ví dụ 2)          │
  │     + tên tải, terminal/số mạch, công suất, CB                         │
  └───────────────────────────────┬──────────────────────────────────────┘
                                   ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  ⑤ XUẤT JSON  (takeoff.json)  →  người duyệt  →  BOQ Excel             │
  └──────────────────────────────────────────────────────────────────────┘
```

> **Đọc tài liệu này theo thứ tự:** TOÀN CẢNH (đang đọc) → **BƯỚC 0** (chặng ③, nền tảng)
> → **VÍ DỤ 1/2/3** (chặng ④, chi tiết gắn cáp). Chặng ②⑤ chỉ cần biết tên.

---

## BƯỚC 0 — Vùng SLD là gì & làm sao biết "đây là MỘT lộ"

### 0A-1. TRƯỚC HẾT: "terminal" là cái gì? (phải hiểu cái này mới hiểu phần sau)

Trong một tủ điện, điện đi theo đường: **nguồn vào → thanh cái (busbar) → chia ra nhiều
NHÁNH đi ra**, mỗi nhánh có 1 aptomat (CB) và **một cái tên ngắn**: `L1`, `S1`, `P1`...

Cái tên ngắn đó chính là **terminal = ĐẦU LỘ / đầu ra của tủ** (đầu cực mà cáp đấu vào).
Quy ước chữ cái:

| Ký hiệu | Nghĩa | Ví dụ tải đi kèm |
|---|---|---|
| **L**1, L2... | **L**ighting — chiếu sáng | đèn, quạt hút |
| **S**1, S2... | **S**ocket — ổ cắm | ổ cắm phòng, ổ cắm bếp |
| **P**1, P2... | **P**ower — động lực | máy nước nóng, dàn nóng ĐH, bếp điện |

Trên bản vẽ, **tất cả nhãn terminal được in thẳng một hàng ngang** (cùng độ cao y). Hàng
đó gọi là **"hàng terminal"**. Trên `ban_ve_goc.pdf` trang 0 có **11 terminal** in cùng
`y = 1226`:

```
   L1   S1   S2   S3   P1   P2   P3   P4   P5   P6   S4     ← HÀNG TERMINAL (y=1226)
  499  536  580  624  667  709  756  802  842  880  947
```

> Vậy "**trên hàng terminal**" = phần bản vẽ nằm **CAO HƠN** hàng này (y nhỏ hơn 1226):
> đó là **thanh cái + các aptomat (nguồn vào)**. Còn "**dưới hàng terminal**" (y > 1226)
> là **cáp + tên tải (đi ra)**. Hàng terminal giống như **cái thắt lưng** cắt ngang sơ đồ
> thành 2 nửa: trên = nguồn, dưới = tải. Nhớ ý này thì phần chia vùng bên dưới sẽ dễ.

---

### 0A-2. "Vùng SLD" là gì & chia vùng thế nào?

Một trang PDF không chỉ có sơ đồ: còn **khung tên, ghi chú, bảng thống kê, logo, sơ đồ
khác**. Nếu quét cả trang, tool sẽ nhặt nhầm chữ/nét của những thứ đó. Nên việc ĐẦU TIÊN
là **khoanh một hình chữ nhật chỉ chứa sơ đồ nguyên lý** = **vùng SLD**; mọi bước sau chỉ
chạy *bên trong* hình này ([`_find_sld_region`](backend/app/core/sld_extractor.py#L107)).

**Hình dung bằng LÁT CẮT DỌC thật** (y nhỏ = trên cao; số THẬT của trang 0):

```
   y ↓ (đi xuống)        NỘI DUNG                         vùng SLD
   ───────────────────────────────────────────────────────────────
   y≈197   DB-2BR-3   ← tên tủ (panel), ở RẤT cao         (ngoài vùng)
                                                           ┌─ y1 = 1006
   1006…1225   thanh cái + aptomat (CB)  ← "TRÊN terminal" │  (nửa NGUỒN)
   ───────────────────────────────────────────────────────┼─ term_y = 1226
   y=1226   L1 S1 S2 P1 ... (HÀNG TERMINAL = thắt lưng)    │
   1267…1302   ═══/═══  các đường CÁP ngang  ← cable_band  │  (nửa TẢI)
   1373…1453   CHIẾU SÁNG, Ổ CẮM... (tên tải, chữ dọc)     │
   y≈1464   cột "2x1C..." (thư viện cáp, góc trái x≈391)   │
                                                           └─ y2 = 1506
```

Tool khoanh hình chữ nhật từ **2 mỏ neo** dễ tìm: **cột cáp `2x1C`** (cho mép trái) và
**hàng terminal** (cho trục ngang giữa). 4 cạnh suy ra:

| Cạnh | Công thức | Tại sao |
|---|---|---|
| trái `x1`=318 | min(x cột `2x1C`) − 40 | bắt đầu từ thư viện cáp bên trái |
| phải `x2`=1067 | max(x terminal) + 120 | hết hàng terminal, chừa lề phải |
| trên `y1`=1006 | **term_y − 220** | lùi LÊN 220pt để ôm trọn thanh cái + CB |
| dưới `y2`=1506 | max(y cột cáp) + 40 | xuống hết phần mô tả cáp |

→ vùng SLD = **[318, 1006, 1067, 1506]**.

#### Xác định "đường (hàng) terminal" như thế nào? — 3 bước

Đây là phần quyết định `term_y`, làm bằng **bình chọn đa số theo hàng**
([sld_extractor.py:113-119](backend/app/core/sld_extractor.py#L113-L119)):

**Bước 1 — Lọc theo MẪU CHỮ.** Trong các chữ NGANG, giữ chữ khớp regex
[`_TERMINAL_RE`](backend/app/core/sld_extractor.py#L38) = `^(?:L|S|P|C)\d+$` hoặc
`^SPARE$`. Tức `L1, S2, P3, C1, SPARE`... Trên trang 0 có **26 chữ** dính mẫu này — nhưng
chúng **rải rác khắp nơi** (khung tên, chú thích, sơ đồ khác), chưa phải hàng terminal.

**Bước 2 — Gom các chữ cùng độ cao vào chung một "hàng".**

Vấn đề: hai chữ trên cùng một hàng hiếm khi có y *y hệt* nhau (vd 1225.6 vs 1225.9). Cần
một cách coi chúng là "cùng hàng". Thủ thuật: **chia y cho 6 rồi làm tròn** → mọi chữ
nằm trong cùng một dải cao 6pt sẽ ra **cùng một con số** (gọi là `key` của hàng):

```
   L1: y=1225.8  →  1225.8 / 6 = 204.30  →  làm tròn = 204  ┐
   S1: y=1225.8  →  1225.8 / 6 = 204.30  →  làm tròn = 204  ├─ cùng key 204
   P6: y=1225.8  →  1225.8 / 6 = 204.30  →  làm tròn = 204  ┘  ⇒ CÙNG HÀNG

   C1: y=1030.8  →  1030.8 / 6 = 171.80  →  làm tròn = 172     ⇒ hàng KHÁC
```

Nói nôm na: `key` giống như **"tầng"** của chữ. Cùng tầng = cùng hàng ngang. Số 6 chỉ là
bề dày mỗi tầng (≈6pt) — đủ rộng để dung sai chênh lệch nhỏ, đủ hẹp để 2 hàng thật không
dính vào nhau.

**Bước 3 — Chọn "tầng" ĐÔNG NHẤT làm hàng terminal.** `term_y` = y trung bình của tầng đó.

##### Bảng dưới đây giải thích vì sao có nhiều dòng

> Nhớ: ở Bước 1 ta vớt được **26 chữ** dính mẫu terminal, **rải khắp trang**. Bước 2 xếp
> chúng vào các tầng. Bảng này liệt kê **TẤT CẢ các tầng** để bạn thấy rõ:
> **chỉ 1 tầng là terminal thật, mọi tầng còn lại là rác** và bị vứt. Các dòng phía dưới
> KHÔNG phải "các hàng terminal khác" — chúng là chữ giống-terminal nhưng nằm ở khung tên,
> chú thích, sơ đồ phụ...

| tầng (`key`) | y≈ | số nhãn trong tầng | các nhãn | KẾT LUẬN |
|---|---|---|---|---|
| **204** | **1225.7** | **11** | **L1 S1 S2 S3 P1 P2 P3 P4 P5 P6 S4** | ✅ **GIỮ — đây là hàng terminal** |
| 43 | 258.8 | 3 | P1 P4 S2 | ❌ rác (khung tên) |
| 45 | 270.9 | 2 | S1 S4 | ❌ rác |
| 172 | 1030.8 | 2 | C1 C2 | ❌ rác (nhãn khác trong sơ đồ) |
| 195 | 1172.0 | 2 | C1 C2 | ❌ rác |
| 33 | 197.6 | 1 | L1 | ❌ rác (dính tên tủ DB-2BR) |
| ... | ... | 1 mỗi tầng | P2, P3, S3, SPARE... | ❌ rác, rải rác |

→ tầng `204` đông áp đảo (**11 nhãn**) → thắng → `term_y = 1225.7`. Mọi tầng ❌ chỉ có
1–3 nhãn nên **không bao giờ thắng** → tự động bị bỏ. Đó là toàn bộ mục đích của bảng:
cho thấy thuật toán **tự lọc rác** mà không cần biết trước hàng terminal ở đâu.

> **Vì sao cách này chắc?** "Đầu lộ" trên bản vẽ buộc phải in **thành một dãy ngang cùng
> cao độ** (đó là bản chất tủ điện). Nên "hàng đông nhãn nhất" gần như chắc chắn là hàng
> terminal — không cần biết trước nó nằm ở y bao nhiêu, tool tự bình chọn ra.

> **Vì sao tách riêng `cable_band`?** Đường CÁP ngang chỉ được dò trong phần **DƯỚI** hàng
> terminal (`term_y+3 → y2`). Lý do nằm ở lát cắt trên: phía TRÊN terminal là **thanh cái
> (busbar)** — cũng là nét ngang dài, nếu không cắt bỏ tool sẽ tưởng thanh cái là một sợi
> cáp. Cắt theo "thắt lưng" terminal là để **chỉ giữ nửa tải.**
>
> **Nếu thiếu cột `2x1C` HOẶC thiếu hàng terminal** → không dựng được vùng → tool báo
> *"Không tìm thấy vùng SLD"* và bỏ trang (đây không phải sơ đồ Kiểu A).

Kiểu B (bảng tủ điện) **không cần** bước khoanh vùng này: nó neo trực tiếp vào từng số
mạch (xem 0B), nên cứ có số mạch là có lộ, ở bất kỳ đâu trên trang.

---

### 0B. Làm sao biết "đây là MỘT lộ"?

**Định nghĩa làm việc của tool:** *một lộ = một CỘT DỌC trên bản vẽ.* Phát hiện lộ =
tìm cái **NEO** của cột. Hai kiểu sơ đồ khác nhau ở chỗ *lấy gì làm neo*.

#### Kiểu A — neo là CHỮ XOAY DỌC TÊN TẢI (KHÔNG phải đường dây dọc!)

> ⚠️ **Hiểu nhầm phổ biến — đọc kỹ.** Trên bản vẽ có **rất nhiều đường dọc thả xuống**
> (dây điện) và nhiều chữ thẳng hàng với chúng. Bạn dễ tưởng tool đếm các **đường dọc**
> đó để ra lộ. **SAI.** Ở Kiểu A, tool **KHÔNG dùng đường dây dọc để phát hiện lộ.**
> Nó chỉ đếm một thứ: **chữ được xoay đứng 90° (chữ dọc) là TÊN TẢI.**

**"Chữ dọc" nghĩa là gì?** Khi trích text, mỗi dòng chữ có một hướng `dir`. Chữ ngang
bình thường có `dir≈(1,0)`; chữ bị **xoay đứng** có `dir≈(0,±1)`. Tool chỉ nhặt loại
xoay đứng ([sld_extractor.py:81-88](backend/app/core/sld_extractor.py#L81-L88)):

```python
d = l.get("dir", (1, 0))
if abs(d[0]) < 0.5:        # ← chỉ giữ chữ XOAY ĐỨNG
    verticals.append(...)
```

Vì sao tên tải lại là chữ dọc? Vì cột lộ hẹp, người vẽ **xoay tên tải đứng lên** cho
vừa. Đó chính là dấu hiệu vàng: *chữ xoay đứng dưới hàng terminal = tên một lộ.*
**Đường dây dọc (nét vẽ) bị bỏ qua hoàn toàn ở bước này.**

**Tại sao "nhiều chữ cũng thẳng đường dọc" mà không bị tính nhầm thành lộ?**
Vì chữ dọc còn phải qua **4 bộ lọc** ([sld_extractor.py:246-255](backend/app/core/sld_extractor.py#L246-L255)).
Đây là số THẬT — quét được nhiều chữ dọc nhưng đa số bị loại:

| Bộ lọc | Loại bỏ chữ dọc nếu... | Vì nó là... |
|---|---|---|
| 1 | bắt đầu `2x1C` | mô tả CÁP (thư viện cáp bên trái) — **không phải tải** |
| 2 | bắt đầu `ỐNG/PVC` | mô tả ỐNG luồn — **không phải tải** |
| 3 | nằm ngoài vùng SLD, hoặc *phía trên* hàng terminal (`y < term_y`) | khung tên / busbar / ghi chú |
| 4 | cách cột cáp < 20pt | dính vào thư viện cáp, không phải cột tải |

Chữ dọc **qua hết 4 lọc** → mỗi cột là **1 lộ**. Hai dòng Việt/Anh cùng trục x (vd
`Ổ CẮM CHO TỦ LẠNH` x=935 + `SOCKET FOR FRIDGE` x=946, lệch ≤14pt) được gộp làm 1 bởi
[`_merge_load_columns`](backend/app/core/sld_extractor.py#L297).

> Trên `ban_ve_goc.pdf` trang 0: sau 4 lọc còn `n_loads = 13` → **13 lộ**. Kiểm tra
> nhanh: `n_slashes = 12` ≈ 13 → gần như mọi lộ đều bắt được cáp; lệch 1 thường là lộ
> **SPARE/dự phòng** (không có cáp nên không cần vạch chéo).

#### "Sao lại lấy L1?" — gán roadName cho lộ

Sau khi có cột lộ (vd `CHIẾU SÁNG` ở **x=491.4**), tool cần biết lộ này cắm vào **đầu cực
(terminal)** nào. Luật **duy nhất**: *terminal có x GẦN NHẤT với cột lộ, trong vòng 60pt*
([sld_extractor.py:269](backend/app/core/sld_extractor.py#L269), `_nearest` + `load_terminal_x_tol=60`).

Hàng terminal thật (cùng y=1226), so với CHIẾU SÁNG ở x=491.4:

```
   L1     S1     S2     S3     P1   ...        ← hàng terminal, y=1226
  499.4  535.9  579.8  623.6  667.3
    ▲
    │ lệch chỉ 8pt  ◄── gần nhất
    491.4  "CHIẾU SÁNG" (chữ dọc, y=1394)
```

| Terminal | x | |Δx| tới CHIẾU SÁNG (491.4) |
|---|---|---|
| **L1** | 499.4 | **8.0** ← nhỏ nhất → chọn |
| S1 | 535.9 | 44.5 |
| S2 | 579.8 | 88.4 |

→ roadName = **"L1"**. Đó là toàn bộ lý do "lấy L1": **không phải tool hiểu L1 là đèn**,
chỉ là **cột chữ "CHIẾU SÁNG" rơi gần ngay dưới nhãn L1 nhất.**

**Bảng gán THẬT của cả trang** (mỗi lộ → terminal gần nhất):

| Lộ (chữ dọc) | x lộ | → Terminal | x term | Δx |
|---|---|---|---|---|
| QUẠT HÚT TOILET | 465.0 | L1 | 499.4 | 34.4 |
| CHIẾU SÁNG | 491.4 | L1 | 499.4 | 8.0 |
| Ổ CẮM BẾP | 527.3 | S1 | 535.9 | 8.6 |
| Ổ CẮM | 570.3 | S2 | 579.8 | 9.5 |
| Ổ CẮM | 614.2 | S3 | 623.6 | 9.4 |
| BẾP ĐIỆN | 660.8 | P1 | 667.3 | 6.5 |
| Ổ CẮM MÁY GIẶT+SẤY | 697–708 | P2 | 709.4 | ~7 |
| MÁY NƯỚC NÓNG | 748.3 | P3 | 755.9 | 7.6 |
| MÁY NƯỚC NÓNG | 794.6 | P4 | 802.1 | 7.5 |
| DÀN NÓNG | 838.3 | P5 | 842.1 | 3.8 |
| DÀN NÓNG | 873.8 | P6 | 880.2 | 6.4 |
| Ổ CẮM TỦ LẠNH | 935.0 | S4 | 947.0 | 12.0 |
| DỰ PHÒNG/SPARE | 1006 | S4 | 947.0 | 59.0 |

> **Nhận xét quan trọng (mặt yếu cần để ý ★★):**
> - **Hai lộ có thể chung 1 terminal** — `QUẠT HÚT TOILET` và `CHIẾU SÁNG` đều về **L1**.
>   Hợp lý: L1 là 1 lộ chiếu sáng cấp cho cả đèn lẫn quạt hút. roadName là **đầu cực/
>   feeder**, nhiều tải dùng chung là bình thường.
> - **Khoảng cách terminal ~40pt nhưng ngưỡng tới 60pt** → nếu một cột lộ rơi đúng **giữa
>   2 terminal**, có thể gán nhầm sang cái bên cạnh. Đa số Δx ở trên chỉ 6–12pt (rất chắc),
>   nhưng `QUẠT HÚT` (34.4) và `SPARE` (59.0) là 2 ca lệch nhiều → **nên người duyệt liếc
>   lại 2 dòng này.**

#### Kiểu B — neo là SỐ MẠCH

Việc tìm danh sách lộ rất gọn: một regex bắt mọi nhãn số mạch
([panel_table.py:25](backend/app/core/takeoff/panel_table.py#L25),
[panel_table.py:79](backend/app/core/takeoff/panel_table.py#L79)):

```python
_REF_RE = r"^(?:S\d+|FCU\s*\d+|SS\d+\.\d+|P\d+|L\d+|C\d+|H\d+)$"
refs = [t for t in horiz if _REF_RE.match(t.text)]   # ← mỗi ref = 1 lộ
```

Khớp `S1`, `S2`, `FCU 1`, `SS1.1`, `P3`...  Trên `Sơ đồ nguyên lý loại 2.pdf`:
`n_refs = 75` → **75 lộ**, gom vào 4 tủ (TĐTM-1, TĐTM-2, TĐTM-3, TĐ-SƯỞI).

##### ⚠️ "Số mạch LẶP LẠI" — lộ = (số mạch + VỊ TRÍ cột), không phải chỉ cái tên

Đây là chỗ dễ nhầm nhất ở Kiểu B. Tên số mạch **không duy nhất**. Trên trang thật,
`"S2"` xuất hiện **3 lần** (số THẬT):

| Lần | toạ độ (x, y) | Thuộc tủ | Tải | Công suất | CB |
|---|---|---|---|---|---|
| 1 | (191, **416**) | TĐTM-1 | Ổ CẮM QUẦY PHA CHẾ | 4000 | RCBO 2P 25A 30mA 6kA |
| 2 | (253, **758**) | TĐTM-2 | Ổ CẮM WC P. NGỦ 1 | 2000 | RCBO 2P 20A 30mA 6kA |
| 3 | (203, **1084**) | TĐTM-3 | Ổ CẮM WC P. NGỦ 1 | 2000 | RCBO 2P 20A 30mA 6kA |

→ **Mỗi lần xuất hiện = 1 lộ riêng.** Một lộ được xác định bởi **(số mạch, trục x, vùng
y)** — chứ không phải chỉ chữ "S2".

##### "Nhiều chữ cũng thẳng cùng trục x" — vì sao không gom nhầm?

Vì mỗi lộ chỉ gom chữ trong **một CỬA SỔ CỘT** quanh đúng cái ref của nó
([panel_table.py:92-94](backend/app/core/takeoff/panel_table.py#L92-L94)):

```python
col = [v for v in verts
       if abs(v.x - ref.x) <= 9              # cùng trục x (±9pt)
       and ref.y - 160 <= v.y <= ref.y - 6]  # và chỉ trong 160pt PHÍA TRÊN ref
```

Hai điều kiện **đồng thời**: cùng trục x **VÀ** nằm trong dải 160pt ngay trên ref. Chính
điều kiện y này chặn việc gom nhầm. Ví dụ THẬT với S2 lần 3 (ref ở y=1084):

```
   y=303   CU/PVC 2X(1X4MM2)...   ← cùng x≈191 NHƯNG Δy=+629 so với ref y=1084
   ...                              → NGOÀI cửa sổ → BỊ LOẠI (thuộc S2 lần 1)
   ┌── cửa sổ cột của S2#3: y ∈ [924 .. 1078] ──┐
   y=968   CU/PVC 2X(1X2.5MM2)...  [CÁP]  ✔ trong cửa sổ
   y=979   ĐI TRONG ỐNG PVC D20    [ỐNG]  ✔
   y=1046  Ổ CẮM WC P. NGỦ 1       [TẢI]  ✔
   └────────────────────────────────────────────┘
   y=1084  S2  ← ref (neo cột)
```

Chữ `CU/PVC ...` ở y=303 tuy **cùng trục x** nhưng cách ref tới **629pt** → ngoài cửa sổ
→ không bị tính cho lộ này (nó thuộc S2 lần 1 ở trên). Đó là lý do "rừng chữ thẳng cột"
không loạn: **mỗi lộ chỉ với tay lên 160pt.**

##### Trong cột, cái nào là cáp / ống / tải? — phân loại theo NỘI DUNG

Không phụ thuộc hàng nào trên/dưới, chỉ nhìn chữ
([panel_table.py:46-53](backend/app/core/takeoff/panel_table.py#L46-L53)):

| Điều kiện nội dung | → Phân loại |
|---|---|
| có `MM2` **và** không có `ỐNG` | **CÁP** |
| có `ỐNG` | **ỐNG luồn** |
| còn lại | **TÊN TẢI** |

Công suất (`power`) và CB lấy từ chữ **NGANG** cùng cột phía trên ref (cửa sổ lệch phải
một chút vì cột CB hay lệch phải so với số mạch) — `4000` → power, `RCBO 2P 25A...` → cb.

##### "Sao lại ra tủ TĐTM-1?" — gán panelName theo CỤM, không theo từng lộ

Tool **không** gán tủ cho từng lộ riêng lẻ (dễ sai). Nó gom các số mạch thành **cụm**
rồi cả cụm dùng chung 1 tên tủ ([`_assign_panels_by_cluster`](backend/app/core/takeoff/panel_table.py#L214)):

1. Chia refs theo **dải y** (mỗi section ngang một dải).
2. Trong mỗi dải, tách **cụm theo khoảng trống x** (2 ref cách > 30pt là sang cụm khác).
3. Mỗi cụm lấy **nhãn tủ gần mép trái cụm nhất, cùng dải y** làm `panelName`.
   (Cụm toàn số mạch `SS...` → đặt tên `TĐ-SƯỞI`.)

Vì vậy S2#1 (y=416) rơi vào cụm của **TĐTM-1**, S2#3 (y=1084) vào cụm **TĐTM-3** — cùng
tên "S2" nhưng khác tủ vì khác cụm.

##### So sánh nhanh A ↔ B (cách phát hiện & gán lộ)

| | Kiểu A | Kiểu B |
|---|---|---|
| Neo của lộ | chữ xoay dọc tên tải | số mạch (chữ ngang) |
| Chống nhầm theo... | 4 bộ lọc + vùng SLD | **cửa sổ cột 160pt** + cùng trục x |
| roadName | terminal gần nhất theo x (±60) | chính là số mạch |
| panelName | nhãn `DB-...` góc trên-trái | gán theo **cụm cột** |
| Tên lặp lại? | tải có thể trùng tên | số mạch trùng tên → phân biệt bằng (x, y) |

#### Bảng so sánh "phát hiện lộ"

| | Neo của lộ | Đếm số lộ bằng | Cần vùng SLD? |
|---|---|---|---|
| **Kiểu A** | cột chữ dọc tên tải | `n_loads` | **Có** (để loại busbar/khung) |
| **Kiểu B** | số mạch (S1, FCU 1...) | `n_refs` | Không (neo trực tiếp) |

**Một câu nhớ:** tool *không thấy* lộ. Nó **tìm cái neo** (tên tải dọc, hoặc số mạch),
gọi đó là MỘT lộ, rồi gom mọi thứ thẳng trục x với neo. Vạch chéo / thẳng cột ở 3 ví dụ
dưới chỉ là bước SAU — **gắn cáp vào lộ đã tìm được.**

---

## VÍ DỤ 1 — "Đèn chiếu sáng này dùng cáp gì?" (sơ đồ Kiểu A: vạch chéo)

📄 Nguồn: `ban_ve_goc.pdf`, trang 0. Kết quả ở `ban_ve_goc.takeoff.json`.

### Bức tranh thật trên bản vẽ (toạ độ thật)

```
        cột của TẢI ở x≈491
                │
  L1   S1   S2  │   ...        ← hàng TERMINAL (đầu lộ), y=1226
  499  536  580 │
                ▼
 cáp#0 ════════/════  y=1267 · 1.5mm²   ← VẠCH CHÉO "/" nằm tại x=492
 cáp#1 ═════════════  y=1279 · 2.5mm²
 cáp#2 ═════════════  y=1291 · 4.0mm²
 cáp#3 ═════════════  y=1302 · 6.0mm²
                │
         "CHIẾU SÁNG / LIGHTING"   (chữ dọc, x=491, y=1394)
```

Có **4 đường cáp ngang** (4 loại tiết diện) và **1 cột tải** tên "CHIẾU SÁNG".
Câu hỏi: tải này ăn **cáp nào trong 4 cáp**?

### Suy luận từng bước (số liệu THẬT)

**Bước 1 — Tìm cột của tải.**
Chữ dọc `"CHIẾU SÁNG/ LIGHTING"` có tâm **x = 491**. Đây là "trục" của lộ này.

**Bước 2 — Tìm vạch chéo "/" gần trục đó nhất.**
Tool quét mọi đoạn thẳng ngắn (5–16pt) nghiêng 25–65° = "vạch chéo". Có **1 vạch chéo ở
x = 492** — lệch trục tải chỉ **0,4pt** (ngưỡng cho phép ≤ 16pt). → khớp.

**Bước 3 — Vạch chéo đó nằm trên đường cáp nào?**
Vạch chéo ở **y ≈ 1267** → trùng **cáp#0** (y=1267). Người vẽ cố ý đặt vạch chéo
ngay chỗ giao của cột tải × đường cáp để nói *"tải này lấy cáp này"*.
→ Cáp = **2x1C 1.5mm² Cu/PVC**, ống = **ỐNG PVC D20**.

**Bước 4 — Lộ này thuộc đầu cực (terminal) nào?**
Trong hàng terminal, cái gần trục x=491 nhất là **L1 (x=499)**, lệch 8pt. → `roadName = "L1"`.

### Kết quả JSON (chính là dòng trong takeoff.json)

```json
{
  "panelName": "DB-2BR",
  "roadName":  "L1",                 // ← Bước 4: terminal gần nhất
  "loadName":  "CHIẾU SÁNG",         // ← Bước 1: tên cột tải
  "size":      "1.5mm2",             // ← Bước 3: lấy mm² đầu của cableSpec
  "cableSpec": "2x1C 1.5mm2 Cu/PVC + 1C-1.5mm2 Cu/PVC (E)",  // ← Bước 2+3: nhờ vạch chéo
  "conduit":   "ỐNG PVC D20/ PVC D20"
}
```

> **Vì sao TIN được?** Vạch chéo là **dấu do người vẽ chủ động đặt**, không phải tool
> đoán. Lệch trục chỉ 0,4pt → gần như không thể nhầm. Đây là liên kết **chắc nhất** (★★★).
> Cách kiểm tra: trong `debug` của trang, `n_loads=13` ≈ `n_slashes=12` → số tải khớp số
> vạch chéo ⇒ hầu hết tải đều bắt được đúng cáp.

---

## VÍ DỤ 2 — "Ổ cắm này dùng cáp gì?" (sơ đồ Kiểu B: bảng cột)

📄 Nguồn: `Sơ đồ nguyên lý loại 2.pdf`, trang 0. Kết quả ở `loai_2.takeoff.json`.

Sơ đồ này **không có vạch chéo**. Thay vào đó nó là **BẢNG**: mỗi lộ là **một cột**,
mọi thứ của lộ đó **xếp thẳng cùng một trục x** rồi neo bởi **số mạch** ở dưới.

### Bức tranh thật (toạ độ thật, cột của số mạch "S2" tại x=203)

```
   y=901   RCBO 2P 20A 30mA 6kA      ← CB (chữ NGANG, trên đầu cột)
   y=1073  2000                      ← công suất 2000W (chữ NGANG)
           ┌───────────────────────────────┐
   y=968   │ CU/PVC 2X(1X2.5MM2) + E.1X2.5MM2 │  [CÁP]   ↑ các chữ DỌC
   y=979   │ ĐI TRONG ỐNG PVC D20            │  [ỐNG]   │ cùng trục x≈203
   y=1041  │ Ổ CẮM WC P. NGỦ 1              │  [TẢI]   │ (lệch ≤ 9pt)
           └───────────────────────────────┘
   y=1084     S2   ← SỐ MẠCH (cái neo cột), x=203
```

### Suy luận từng bước (số liệu THẬT)

**Bước 1 — Tìm "cái neo cột".**
`"S2"` ở (x=203, y=1084) khớp mẫu số mạch `S\d+` → đây là **cột cần bóc**, trục x=203.

**Bước 2 — Gom mọi chữ DỌC thuộc cột này.**
Điều kiện: `|x − 203| ≤ 9pt` **và** nằm **phía trên** S2 trong vòng 160pt. Tìm được 3 chữ:
| Chữ | y | Phân loại theo NỘI DUNG |
|---|---|---|
| `CU/PVC 2X(1X2.5MM2) + E.1X2.5MM2` | 968 | có "MM2", không có "ỐNG" → **CÁP** |
| `ĐI TRONG ỐNG PVC D20` | 979 | có "ỐNG" → **ỐNG luồn** |
| `Ổ CẮM WC P. NGỦ 1` | 1041 | còn lại → **TÊN TẢI** |

**Bước 3 — Lấy công suất & CB từ chữ NGANG cùng cột.**
Phía trên S2, cùng trục x (lệch phải ≤14pt): số thuần `2000` → **power**; cụm
`RCBO 2P 20A 30mA 6kA` → **cb**.

### Kết quả JSON

```json
{
  "panelName": "TĐTM-...",
  "roadName":  "S2",                            // ← Bước 1: số mạch neo cột
  "loadName":  "Ổ CẮM WC P. NGỦ 1",            // ← Bước 2: chữ dọc không phải cáp/ống
  "power":     "2000",                          // ← Bước 3
  "cb":        "RCBO 2P 20A 30mA 6kA",          // ← Bước 3
  "size":      "2.5mm2",
  "cableSpec": "CU/PVC 2X(1X2.5MM2) + E.1X2.5MM2",  // ← Bước 2 (thẳng cột)
  "conduit":   "ỐNG PVC D20"                    // ← Bước 2 (đã bỏ "ĐI TRONG")
}
```

> **Vì sao TIN được?** "Thẳng cùng trục x" là quy ước bảng vẽ rất mạnh (★★★). Phân loại
> cáp/ống/tải dựa vào **nội dung chữ** ("MM2", "ỐNG") nên không phụ thuộc toạ độ tuyệt đối,
> linh hoạt với nhiều cách trình bày.

---

## VÍ DỤ 3 — "Công tắc nào điều khiển đèn?" (Hệ Knowledge Graph)

📄 Nguồn: `ban_ve_goc.pdf`, trang 0. Kết quả ở `ban_ve_goc.analysis.json`.

Đây là hệ **khác** với 2 ví dụ trên: nó tìm quan hệ **điều khiển / cấp nguồn** bằng cách
**lần theo ĐƯỜNG DÂY thật** trên bản vẽ. 4 bước:

**Bước 1 — Mỗi nhãn chữ thành 1 "thực thể" (node).**
`S1` (công tắc), `L1` (đèn), `1P-20A` (aptomat)… mỗi cái 1 node, đặt tại tâm chữ.

**Bước 2 — Dựng "mạng dây".**
Gom mọi nét thuộc layer dây (`group:"wire"`). Hai đầu dây cách nhau < 3pt được coi là
**cùng 1 nút mạng**. Nối tất cả → ra các **mạng dây rời nhau** (dùng thư viện NetworkX).

```
   S1 ●─────┐
            ├──────● 1P-20A ──────● L1     ← cùng MỘT mạng dây
   S2 ●─────┘                              ⇒ các thiết bị này "liên thông"
   S3 ●─────┘
```

**Bước 3 — Gắn thiết bị vào mạng & nối thành chuỗi.**
Mỗi node tìm nút dây gần nhất (≤55pt). Các node rơi vào **cùng một mạng** được nối
`connected_to`. Trích thật từ analysis.json:
```json
{ "source": "p0.L1", "target": "p0.S1", "relation": "connected_to", "weight": 36.5 }
{ "source": "p0.S1", "target": "p0.1P-20A", "relation": "connected_to", "weight": 48.9 }
```

**Bước 4 — Suy ra quan hệ có nghĩa.**
Luật: *trong một mạng, nếu có công tắc + có đèn → công tắc điều khiển đèn.*
```json
{ "rule": "Rule1", "subject": "S1", "relation": "controls", "objects": ["L1"],
  "detail": "Công tắc S1 điều khiển 1 đèn" }
```

> ⚠️ **Đây là chỗ KÉM CHẮC hơn (★★) — cần người duyệt.** Trên trang này, mạng đó chứa
> **cả S1, S2, S3** + L1, nên tool kết luận **cả 3 công tắc** đều điều khiển L1. Có thể
> đúng (mạch đảo chiều 3 nơi), nhưng cũng có thể do **mạng dây bị gộp nhầm**. Khác hẳn
> Ví dụ 1–2 (có bằng chứng vạch chéo / thẳng cột), ở đây bằng chứng chỉ là "cùng nối một
> đám dây" → đó là lý do có bước con người xác nhận trước khi xuất BOQ.

---

## Tóm tắt: 3 kiểu suy luận & cách biết đúng

| Ví dụ | Câu hỏi | Liên kết NHỜ | Độ chắc | Cách kiểm tra |
|---|---|---|---|---|
| 1. busbar_slash | tải ↔ cáp | **vạch chéo "/"** trùng trục x | ★★★ | `n_loads ≈ n_slashes`; lệch trục nhỏ |
| 2. panel_table | tải ↔ cáp | **thẳng cùng trục x** dưới số mạch | ★★★ | mỗi cột có đủ cáp/ống/tải |
| 3. knowledge graph | công tắc ↔ đèn | **đường dây nối liền** | ★★ | `weight` nhỏ; soi mạng có bị gộp dư |

**Quy tắc vàng để tự kiểm tra một liên kết bất kỳ:**
1. Mở `debug` của trang trong takeoff.json (n_routes/n_slashes/n_loads…).
2. Xem `weight` của cạnh (= khoảng cách): càng nhỏ càng tin.
3. Nghi ngờ → mở `*.raw_full.json`, tra đúng toạ độ 2 thực thể xem chúng có thật sự

   thẳng hàng / có vạch chéo / có dây nối không.
4. Liên kết ★★ (Hệ knowledge graph, located_in, cross_ref) **luôn nên để người duyệt**
   trước khi chốt BOQ.
