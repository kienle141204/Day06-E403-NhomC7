# Workflow — Chatbot Đọc Đơn Thuốc (v2)

## Tổng quan

Chatbot giúp bệnh nhân hiểu đơn thuốc sau khi khám, thay vì phải gọi lại bác sĩ hoặc tự tra Google. Người dùng upload ảnh đơn thuốc → AI validate tài liệu → đọc và trích xuất theo từng thuốc → user xác nhận → thu thập context → kiểm tra tương tác → Q&A có kiểm soát → tạo nhắc uống thuốc → tóm tắt.

**Nguyên tắc thiết kế:**
- AI không bao giờ giải thích thuốc trước khi user xác nhận tên đúng
- Confidence check ở mức từng thuốc, không cộng gộp toàn đơn
- Mọi câu hỏi về thay đổi liều/ngừng thuốc đều chuyển chuyên gia
- Emergency detection chạy song song xuyên suốt Q&A loop
- Escalation path (nút hỏi dược sĩ) luôn hiển thị ở mọi màn hình

---

## Luồng chính (Main Flow)

```
┌─────────────────────────────────────────────────────────────┐
│  [0] VALIDATE DOCUMENT — KIỂM TRA TÀI LIỆU                 │
│      Trước khi OCR: phân tích ảnh có phải đơn thuốc không  │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
   Là đơn thuốc               Không phải đơn thuốc
   (toa bác sĩ,               (hóa đơn, bao bì,
   đơn bệnh viện)             ảnh thuốc, toa ăn)
           │                          │
           │                          ▼
           │                 Thông báo + Yêu cầu
           │                 upload lại đúng tài liệu
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  [1] USER UPLOAD ẢNH ĐƠN THUỐC                             │
│      Chụp ảnh hoặc upload file                              │
│      Hỗ trợ nhiều ảnh cho đơn nhiều trang                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  [2] OCR — TRÍCH XUẤT THEO TỪNG THUỐC                      │
│                                                             │
│  Với mỗi thuốc trong đơn, trích xuất:                      │
│  • Tên thuốc + confidence riêng                             │
│  • Liều lượng + đơn vị (mg, g, ml, v.v.)                   │
│  • Tần suất — chuẩn hóa viết tắt:                         │
│    od → 1 lần/ngày   bid → 2 lần/ngày                      │
│    tid → 3 lần/ngày  qid → 4 lần/ngày                      │
│  • Thời điểm uống:                                          │
│    ac → trước ăn     pc → sau ăn     hs → trước ngủ        │
│  • Loại: Regular / PRN (khi cần) + giới hạn tối đa/ngày   │
│  • Ngày kê đơn + thời gian điều trị (số ngày)              │
│  • Chú thích đặc biệt của bác sĩ                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  [3] DRUG-LEVEL CONFIDENCE CHECK + KIỂM TRA HẠN ĐƠN       │
│                                                             │
│  Mỗi thuốc có ngưỡng riêng — không cộng gộp toàn đơn:     │
│                                                             │
│  ≥ 80%  → Badge "Đã nhận dạng" (xanh)                      │
│  < 80%  → Badge "Cần xác nhận" (cam) + highlight field     │
│  Không đọc được → Badge "Không đọc được" + ô nhập tay      │
│                                                             │
│  Kiểm tra hạn đơn song song:                               │
│  Ngày kê > 30 ngày → Cảnh báo: "Đơn kê [X ngày] trước.   │
│  Xác nhận với bác sĩ/dược sĩ trước khi dùng."             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  [4] USER XÁC NHẬN VÀ CHỈNH SỬA ĐƠN THUỐC                 │
│                                                             │
│  Hiển thị dạng card từng thuốc với đầy đủ các field        │
│  User có thể:                                               │
│  • Sửa bất kỳ field nào (tên, liều, tần suất, giờ uống)   │
│  • Thêm thuốc nếu OCR bỏ sót                               │
│  • Xóa dòng nếu OCR nhận nhầm                              │
│                                                             │
│  AI KHÔNG bắt đầu giải thích cho đến khi                   │
│  user bấm "Xác nhận đơn thuốc này"                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  [5] CONTEXT COLLECTION — THÔNG TIN USER (TÙY CHỌN)        │
│                                                             │
│  "Để tư vấn chính xác hơn, bạn có thể cho biết:"          │
│  □ Bạn đang mang thai hoặc cho con bú?                     │
│  □ Bạn có dị ứng thuốc nào không?                          │
│  □ Bạn đang dùng thêm thuốc nào khác?                     │
│                                                             │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
    User điền thông tin          User bấm "Bỏ qua"
           │                          │
           ▼                          ▼
  Dùng context trong          Tiếp tục với lời khuyên
  bước 6 + Q&A               chung + thêm disclaimer
           │                          │
           └──────────┬───────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  [6] DRUG INTERACTION CHECK — KIỂM TRA TƯƠNG TÁC THUỐC    │
│                                                             │
│  Kiểm tra tương tác giữa các thuốc trong đơn với nhau      │
│  + với thuốc khác user đang dùng (nếu khai ở bước 5)       │
│                                                             │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
   Không phát hiện             Phát hiện tương tác
   tương tác đáng              nguy hiểm
   lo ngại                            │
           │                          ▼
           │                 Hiển thị cảnh báo cụ thể
           │                 (ví dụ: Warfarin + Aspirin
           │                 → tăng nguy cơ chảy máu)
           │                 + Yêu cầu hỏi dược sĩ
           │                 trước khi dùng đồng thời
           │                          │
           └──────────┬───────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  [7] Q&A LOOP — CHATBOT TRẢ LỜI CÓ KIỂM SOÁT              │
│                                                             │
│  TRONG PHẠM VI AI TRẢ LỜI:                                 │
│  • "Thuốc này dùng để làm gì?"                             │
│  • "Uống trước hay sau ăn?"                                 │
│  • "Tác dụng phụ thường gặp là gì?"                        │
│  • "Bỏ lỡ 1 liều thì sao?"                                 │
│  • "Bảo quản thuốc này thế nào?"                           │
│  • "Thuốc này có gây buồn ngủ không?"                      │
│                                                             │
│  AI TỪ CHỐI + CHUYỂN CHUYÊN GIA:                           │
│  • "Có nên tăng/giảm liều không?"                          │
│    → "Quyết định liều thuộc về bác sĩ."                    │
│  • "Có nên ngừng thuốc không?"                             │
│    → Từ chối + cảnh báo ngừng đột ngột                     │
│  • "Thuốc này có chữa được bệnh [X] không?"               │
│    → Từ chối chẩn đoán + gợi ý gặp bác sĩ                 │
│                                                             │
│  CORRECTION TRONG Q&A:                                      │
│  Nếu user nói "Thực ra liều là..." / "Tên thuốc sai rồi"  │
│  → Cho phép quay lại Bước 4 để cập nhật mà không           │
│    restart session                                          │
│                                                             │
│  ⚠️ EMERGENCY DETECTION (chạy song song mọi lúc):          │
│  Từ khóa: khó thở, phát ban nặng, sưng phù, tim đập        │
│  bất thường, mất ý thức, dị ứng nặng                       │
│  → Dừng Q&A ngay, hiển thị:                                │
│    "Gọi ngay 115 hoặc đến cơ sở y tế gần nhất.            │
│     Đừng tự dùng thêm thuốc."                              │
│                                                             │
│  [Lặp lại cho đến khi user không còn câu hỏi]             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  [8] DANGEROUS DRUG CHECK — CẢNH BÁO THUỐC NGUY HIỂM      │
│                                                             │
│  Phân loại cụ thể, không chỉ "thuốc nguy hiểm chung":     │
│  • Hóa trị / ung thư                                        │
│  • Thuốc tâm thần (antipsychotics, antidepressants)        │
│  • Thuốc tim mạch liều cao (digoxin, warfarin, amiodarone) │
│  • Corticosteroid dài ngày (prednisolone, dexamethasone)   │
│  • Thuốc tiểu đường (insulin, sulfonylurea)                 │
│  • Thuốc chống đông máu                                     │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
   Đơn thông thường           Thuốc thuộc nhóm nguy hiểm
   (kháng sinh, giảm đau,            │
   hạ sốt, dạ dày...)                ▼
           │                 Cảnh báo cụ thể theo loại thuốc
           │                 + Gợi ý đặt lịch tư vấn
           │                 bác sĩ / dược sĩ chuyên khoa
           │                          │
           └──────────┬───────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  [9] REMINDER SETUP — TẠO LỊCH UỐNG THUỐC                  │
│                                                             │
│  Phân loại trước khi tạo reminder:                         │
│                                                             │
│  REGULAR MEDICATION                                         │
│  → Tạo reminder lịch cố định, nhắc trước 1h               │
│  → Nếu thuốc phụ thuộc bữa ăn: hỏi giờ ăn của user       │
│                                                             │
│  PRN MEDICATION (khi cần)                                   │
│  → Không tạo reminder lịch                                  │
│  → Tạo reminder "giới hạn": "Không dùng quá [X] lần/ngày" │
│                                                             │
│  TIMING CONFLICT GIỮA CÁC THUỐC                            │
│  Ví dụ: sắt cần cách canxi 2h, antacid cách kháng sinh 2h │
│  → Phát hiện conflict → Suggest giờ tự động có khoảng      │
│    cách đủ → Hiển thị để user xác nhận                     │
│                                                             │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
  Có lịch uống cụ thể         Chỉ có PRN / không có
           │                  lịch cụ thể
           ▼                          │
  User đồng ý → Tạo reminder         ▼
  User từ chối → Bỏ qua     Hiển thị giới hạn PRN
           │                 + Kết thúc session
           │                          │
           └──────────┬───────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  [10] KẾT THÚC SESSION — TÓM TẮT ĐẦY ĐỦ                   │
│                                                             │
│  Hiển thị:                                                  │
│  • Danh sách thuốc + cách uống + lịch nhắc đã đặt          │
│  • Ngày kết thúc điều trị (nếu OCR trích được)             │
│  • ⚠️ Cảnh báo tương tác (nếu có từ Bước 6)               │
│  • ⚠️ Cảnh báo thuốc nguy hiểm (nếu có từ Bước 8)         │
│  • Disclaimer cố định:                                      │
│    "Thông tin chỉ mang tính tham khảo.                     │
│     Hãy xác nhận với bác sĩ / dược sĩ của bạn."           │
│  • Nút "Hỏi dược sĩ Long Châu" — luôn hiển thị            │
└─────────────────────────────────────────────────────────────┘
```

---

## Four Paths

### Happy Path — Đơn thuốc rõ ràng, thông thường

```
User upload ảnh đơn rõ nét
    → [0] Document validation pass
    → [2] OCR trích xuất 3 thuốc: Amoxicillin 500mg tid pc,
           Omeprazole 20mg od ac, Paracetamol 500mg prn max 4 lần/ngày
    → [3] Cả 3 thuốc confidence ≥ 80% → badge xanh hết
           Ngày kê đơn: hôm qua → không cảnh báo hạn
    → [4] Hiển thị 3 card thuốc → User xác nhận "Đúng rồi"
    → [5] User điền: không mang thai, không dị ứng, không uống thuốc khác
    → [6] Không phát hiện tương tác nguy hiểm → hiển thị "Không phát hiện tương tác"
    → [7] User hỏi: "Amoxicillin uống trước hay sau ăn?"
           AI trả lời: "Amoxicillin uống sau ăn (pc) để giảm kích ứng dạ dày..."
    → [8] Đơn thông thường → không cảnh báo nguy hiểm
    → [9] Regular: Amoxicillin (sáng/trưa/tối sau ăn) → tạo 3 reminder/ngày
           Regular: Omeprazole (sáng trước ăn) → tạo 1 reminder/ngày
           PRN: Paracetamol → tạo reminder giới hạn "max 4 lần/ngày"
    → [10] Summary hiển thị đầy đủ
```

**Kết quả:** User biết cách uống đúng, có lịch nhắc, hiểu giới hạn thuốc khi cần.

---

### Low-confidence Path — Ảnh mờ hoặc tên thuốc lạ

```
User upload ảnh đơn chụp thiếu sáng / bác sĩ viết tay
    → [0] Document validation pass (vẫn nhận ra là đơn thuốc)
    → [2] OCR trích xuất 3 thuốc:
           Thuốc 1: confidence 88% → OK
           Thuốc 2: confidence 55% → "Metf???in 500mg" → badge cam
           Thuốc 3: không đọc được → badge đỏ + ô nhập tay
    → [3] Chỉ flag Thuốc 2 và Thuốc 3, Thuốc 1 vẫn hiển thị bình thường
    → [4] User xác nhận:
           Thuốc 1: OK
           Thuốc 2: sửa thành "Metformin 500mg"
           Thuốc 3: nhập tay "Glibenclamide 5mg"
    → Tiếp tục flow bình thường từ [5]
```

**Kết quả:** Chỉ yêu cầu user sửa những thuốc thật sự cần sửa, không làm phiền toàn bộ quy trình.

---

### Failure Path — OCR đọc nhầm nhưng confidence vẫn cao

```
User upload ảnh đơn
    → [2] OCR đọc nhầm: "Metronidazole 500mg" (đúng ra là Metformin 500mg)
           confidence: 82% → vẫn badge xanh
    → [4] Hiển thị card "Metronidazole 500mg" để user xác nhận
    → User nhìn đơn gốc, phát hiện: "Không phải, đây là Metformin"
    → User sửa trong card → AI cập nhật
    → [6] Sau khi sửa, interaction check chạy lại với tên thuốc đúng
    → Tiếp tục flow bình thường
```

**Kết quả:** Lỗi OCR được bắt trước khi gây hại. Bước xác nhận bắt buộc là lớp phòng thủ cuối.

---

### Correction Path — User sửa thông tin sau khi đã xác nhận

```
Scenario A — Sửa reminder sau khi đã tạo:
    User xác nhận đơn → AI tạo reminder "Omeprazole uống lúc 7h sáng"
    → User: "Tôi hay ăn sáng lúc 8h, đổi sang 7h30 được không?"
    → AI cập nhật reminder → Hiển thị lịch mới để user xác nhận

Scenario B — Phát hiện liều sai trong lúc Q&A:
    User hỏi về Metformin → AI giải thích dựa trên 500mg đã xác nhận
    → User: "Nhưng trên vỏ hộp ghi 1000mg, OCR sai rồi"
    → AI: "Cho phép bạn quay lại cập nhật đơn"
    → User sửa liều 500mg → 1000mg trong Bước 4 (không restart session)
    → AI tiếp tục giải thích dựa trên liều đã sửa
```

**Kết quả:** User có thể điều chỉnh ở bất kỳ thời điểm nào trong session mà không phải bắt đầu lại.

---

## Failure Modes và Mitigation

### Failure Mode 1 (từ workflow cũ) — OCR đọc nhầm tên thuốc

```
Trigger:   User tin tưởng kết quả AI mà không kiểm tra tên thuốc
Failure:   OCR đọc nhầm "Metformin" → "Metronidazole"
           AI giải thích công dụng thuốc kháng sinh thay vì thuốc tiểu đường
Impact:    User uống sai thuốc, bỏ lỡ liều trị bệnh chính, nguy hiểm sức khỏe

Mitigation:
  Bước 4: Xác nhận bắt buộc — AI không giải thích trước khi user confirm
  Bước 4: Hiển thị card rõ ràng để user so sánh với đơn gốc
  Bước 10: Disclaimer cố định ở mọi màn hình
```

### Failure Mode 2 (MỚI) — Tương tác thuốc không được cảnh báo

```
Trigger:   Đơn thuốc có 2 thuốc tương tác nguy hiểm
Failure:   AI giải thích từng thuốc riêng lẻ, không phát hiện combo
           Ví dụ: Warfarin + Aspirin → tăng nguy cơ chảy máu nghiêm trọng
Impact:    User dùng đồng thời mà không biết rủi ro

Mitigation:
  Bước 6: Drug Interaction Check chạy trước Q&A
  Kết quả luôn hiển thị (kể cả "Không phát hiện tương tác") — không bao giờ im lặng
  Tương tác nguy hiểm → yêu cầu xác nhận với dược sĩ trước khi dùng
```

### Failure Mode 3 (MỚI) — User thuộc nhóm đặc biệt nhưng AI không biết

```
Trigger:   User mang thai hỏi về thuốc có contraindication với thai kỳ
           (ví dụ: Methotrexate, NSAIDs liều cao, Warfarin)
Failure:   AI trả lời theo thông tin chung, không cảnh báo thai kỳ
Impact:    User dùng thuốc có thể gây hại thai nhi

Mitigation:
  Bước 5: Context Collection hỏi về thai kỳ, cho con bú, dị ứng
  Nếu user khai mang thai → flag pregnancy trong session
  Tất cả câu trả lời Q&A sẽ kèm pregnancy warning nếu có liên quan
  Thuốc contraindicated với thai kỳ → cảnh báo ngay + chuyển dược sĩ
```

### Failure Mode 4 (MỚI) — User mô tả triệu chứng cấp cứu trong Q&A

```
Trigger:   User đang hỏi về thuốc, đề cập triệu chứng nguy hiểm
           "Tôi vừa uống thuốc xong thì khó thở và nổi mề đay toàn thân"
Failure:   AI tiếp tục Q&A bình thường, giải thích tác dụng phụ nhẹ nhàng
Impact:    User không nhận ra đây là cấp cứu, không gọi 115 kịp

Mitigation:
  Emergency Detection chạy song song trong toàn bộ Q&A loop
  Từ khóa trigger: khó thở, phát ban nặng, sưng phù, tim đập bất thường,
    mất ý thức, choáng váng dữ dội, đau ngực
  Khi phát hiện: dừng Q&A ngay, hiển thị:
    "⚠️ KHẨN CẤP: Gọi ngay 115 hoặc đến cơ sở y tế gần nhất.
     Đừng tự dùng thêm thuốc."
```

### Failure Mode 5 (MỚI) — User upload đơn thuốc cũ hết hạn

```
Trigger:   User tìm lại đơn thuốc từ 2–3 tháng trước và upload
Failure:   AI giải thích và tạo reminder như đơn còn hiệu lực
Impact:    User dùng thuốc không theo chỉ định điều trị hiện tại của bác sĩ

Mitigation:
  Bước 3: Trích xuất ngày kê đơn từ OCR
  Nếu ngày kê > 30 ngày: cảnh báo nổi bật ngay sau OCR
    "Đơn thuốc này được kê [X ngày] trước.
     Hãy xác nhận với bác sĩ/dược sĩ trước khi tiếp tục."
  Session vẫn tiếp tục để user hiểu đơn thuốc,
  nhưng reminder không được tạo cho đơn hết hạn
```

---

## Các Tool và AI Decision Points

| Bước | Tool / AI | Decision | Output |
|---|---|---|---|
| [0] Document Validation | Vision model | Phân biệt đơn thuốc với hóa đơn/bao bì/ảnh khác | Pass / Fail + yêu cầu upload lại |
| [2] OCR | Vision model (GPT-4o / Claude) | Trích xuất text theo từng thuốc | Structured drug list với confidence mỗi drug |
| [2] Abbreviation Parser | Rule-based | Chuẩn hóa: od→1x, bid→2x, ac→trước ăn, prn→khi cần | Frequency + timing chuẩn |
| [3] Drug-level Confidence | Rule-based | Ngưỡng ≥ 80% mỗi thuốc riêng lẻ | Badge xanh/cam/đỏ theo từng thuốc |
| [3] Prescription Date Check | Rule-based | So sánh ngày kê đơn với ngày hiện tại | Cảnh báo hạn nếu > 30 ngày |
| [5] Context Collection | UX form | Thu thập thai kỳ, dị ứng, thuốc đang dùng | Context object cho session |
| [6] Drug Interaction Check | Rule-based database + LLM | Cross-check cặp thuốc trong đơn + thuốc khác | Danh sách tương tác nguy hiểm (nếu có) |
| [7] Q&A | LLM + drug knowledge base | Trả lời trong phạm vi an toàn, từ chối ngoài phạm vi | Câu trả lời / từ chối có giải thích |
| [7] Q&A Boundary | Rule-based | Phát hiện câu hỏi về đổi liều/ngừng thuốc/chẩn đoán | Redirect sang chuyên gia |
| [7] Emergency Detection | Keyword + LLM | Phát hiện mô tả triệu chứng cấp cứu | Ngắt Q&A + hiển thị emergency alert |
| [8] Dangerous Drug Check | Rule-based + LLM | Phân loại nhóm thuốc nguy hiểm cụ thể | Cảnh báo theo loại + gợi ý booking |
| [9] Reminder | App notification API | Phân biệt regular / prn, phát hiện timing conflict | Reminder schedule + conflict warning |
| [9] Timing Conflict Resolver | Rule-based | Phát hiện thuốc cần cách nhau | Đề xuất giờ uống có khoảng cách đủ |
| [10] Booking | Booking API (nếu có) | Gợi ý / đặt lịch bác sĩ / dược sĩ | Link booking |

---

## Backlog (không build trong Day 06)

- Tích hợp database thuốc Việt Nam đầy đủ (tra cứu offline)
- Nhận dạng chữ viết tay bác sĩ độ chính xác cao
- Kiểm tra tương tác thuốc giữa nhiều đơn thuốc khác nhau (cross-prescription)
- Lịch sử đơn thuốc theo thời gian + so sánh đơn cũ/mới
- Kết nối trực tiếp với hệ thống đặt lịch bệnh viện
- Hỗ trợ đa ngôn ngữ (Anh, Hoa cho đơn thuốc nhập)
- Cá nhân hóa theo hồ sơ bệnh án / bệnh nền dài hạn
- Dashboard dược sĩ review ca nguy hiểm
- Tích hợp bảo hiểm y tế / y bạ điện tử
- Kiểm chứng lâm sàng câu trả lời AI
- Auto-order thuốc từ đơn (kết nối kho Long Châu)
- Session continuity — user quay lại hỏi thêm sau nhiều ngày
