# MedChat — Tài liệu kiểm thử 4 kịch bản

## Tổng quan

Kịch bản được kích hoạt tự động dựa trên **tiền tố tên file** khi upload. Không cần thay đổi UI hay cấu hình.

| # | Kịch bản | Tên file upload | Luồng kiểm thử |
|---|----------|-----------------|----------------|
| 1 | Đơn thuốc đơn giản | `scenario1.jpg` hoặc `don-gian.jpg` | Upload → Xác nhận → Chat tự do |
| 2 | Đơn thuốc nguy hiểm | `scenario2.jpg` hoặc `nguy-hiem.jpg` | Upload → Xác nhận → Chat bị chặn → Đặt lịch bác sĩ |
| 3 | Đơn thuốc không rõ | `scenario3.jpg` hoặc `khong-ro.jpg` | Upload → Sửa thuốc → Xác nhận → Chat |
| 4 | Không đọc được ảnh | `scenario4.jpg` hoặc `khong-doc.jpg` | Upload → Lỗi → Upload lại |

> **Lưu ý:** Tên file case-insensitive. Mọi file không khớp tiền tố nào sẽ chạy Kịch bản 1 (mặc định).

---

## Kịch bản 1 — Đơn thuốc đơn giản

### Mục tiêu
Kiểm thử luồng cơ bản hoàn chỉnh: upload → xem đơn → xác nhận → chat tư vấn.

### File upload
`scenario1.jpg` (hoặc bất kỳ ảnh nào đổi tên thành `scenario1.jpg`)

### Dữ liệu mock
- **Bác sĩ:** BS. Nguyễn Thị Hoa — Phòng khám Đa khoa Bình Dân
- **Độ tin cậy tổng thể:** 92%
- **Thuốc:**
  - Amoxicillin 500mg — 1 viên, sáng/trưa/tối sau ăn, 7 ngày — `risk: normal`, confidence 93%
  - Paracetamol 500mg — 1–2 viên khi sốt/đau (cách 4–6 giờ), 5 ngày — `risk: normal`, confidence 97%
  - Cetirizine 10mg — 1 viên tối trước khi ngủ, 7 ngày — `risk: normal`, confidence 88%
- **Cảnh báo:** Không có

### Các bước kiểm thử
1. Upload file `scenario1.jpg`
2. ✅ Panel bên phải hiện: 3 thuốc, badge "Cần bạn kiểm tra", confidence **92%**
3. ✅ Header chat hiện biểu tượng shield xanh (không phải cảnh báo)
4. Gõ **"xác nhận"** hoặc nhấn quick reply "Xác nhận đơn thuốc"
5. ✅ Badge đổi sang "Đã xác nhận" (màu xanh lá)
6. ✅ Bot nhắn: "Đơn thuốc đã được xác nhận. Bây giờ bạn có thể hỏi..."
7. Gõ **"tác dụng phụ"**
8. ✅ Bot trả lời về tác dụng phụ của Amoxicillin và Paracetamol
9. Gõ **"lịch uống"**
10. ✅ Bot trả lời về lịch uống trong ngày
11. Nhấn quick reply **"Tạo nhắc uống thuốc"**
12. ✅ Nhắc nhở được tạo và hiển thị trong panel

### Kết quả mong đợi
- Xác nhận thành công ngay, không bị chặn
- Chat tư vấn hoạt động tự do
- Tạo nhắc và đặt lịch đều hoạt động

---

## Kịch bản 2 — Đơn thuốc nguy hiểm

### Mục tiêu
Kiểm thử: chatbot chặn tư vấn cho đơn có thuốc nguy cơ cao, hướng người dùng đến đặt lịch với bác sĩ chuyên khoa.

### File upload
`scenario2.jpg` (hoặc `nguy-hiem.jpg`)

### Dữ liệu mock
- **Bác sĩ:** BS. Trần Quốc Bảo — Bệnh viện Đa khoa Trung Ương
- **Độ tin cậy tổng thể:** 89%
- **Thuốc:**
  - Warfarin 5mg — 1 viên tối cùng giờ mỗi ngày, 30 ngày — **`risk: HIGH`**, confidence 91%
  - Digoxin 0.25mg — 1 viên sáng trước ăn, 30 ngày — **`risk: HIGH`**, confidence 87%
  - Furosemide 40mg — 1 viên sáng sau ăn, 14 ngày — `risk: normal`, confidence 94%
- **Cảnh báo:**
  - 🔴 "Thuốc kháng đông nguy cơ cao" — Warfarin có khoảng điều trị hẹp, không tự ý đổi liều
  - 🔴 "Glycoside tim — theo dõi nhịp" — Digoxin cần theo dõi nhịp tim và điện giải đồ

### Các bước kiểm thử
1. Upload file `scenario2.jpg`
2. ✅ Panel hiện 2 thuốc nền đỏ (Warfarin, Digoxin), 1 thuốc bình thường
3. ✅ Panel hiện 2 cảnh báo màu đỏ
4. ✅ Header chat hiện biểu tượng alert đỏ/vàng
5. Gõ **"xác nhận"** → xác nhận thành công
6. Gõ bất kỳ câu hỏi (ví dụ: **"thuốc này uống như thế nào?"**)
7. ✅ Bot **CHẶN** và hiển thị: "Đơn thuốc này chứa thuốc có nguy cơ cao. Để đảm bảo an toàn, tôi không thể tư vấn trực tiếp. Vui lòng đặt lịch với bác sĩ."
8. ✅ Quick replies: **["Đặt lịch với bác sĩ", "Xem cảnh báo"]**
9. Nhấn **"Đặt lịch với bác sĩ"**
10. ✅ Panel hiện danh sách chuyên gia:
    - BS. CKI. Lê Minh Khoa — Tim mạch & Chống đông
    - DS. Phạm Thị Thu — Dược lâm sàng
11. Nhấn "Đặt lịch" với một chuyên gia
12. ✅ Lịch hẹn được xác nhận

### Kết quả mong đợi
- Xác nhận thành công
- **Mọi** tin nhắn chat đều bị chặn sau xác nhận
- Chỉ luồng đặt lịch bác sĩ được phép tiếp tục
- Chuyên gia hiển thị đúng chuyên khoa tim mạch

---

## Kịch bản 3 — Đơn thuốc không rõ ràng

### Mục tiêu
Kiểm thử: khi OCR nhận dạng kém, hệ thống buộc người dùng phải sửa đúng tên thuốc trước khi xác nhận và chat.

### File upload
`scenario3.jpg` (hoặc `khong-ro.jpg`)

### Dữ liệu mock
- **Bác sĩ:** BS. ??? (không rõ)
- **Độ tin cậy tổng thể:** 45% ⚠️
- **Thuốc:**
  - "??? (Thuốc X...)" — không rõ — `risk: normal`, **confidence 32%** (cần sửa)
  - Paracetamol 500mg — khi sốt, 5 ngày — `risk: normal`, confidence 85% ✅
  - "Thuốc Y (không đọc được)" — không rõ — `risk: normal`, **confidence 41%** (cần sửa)
- **Cảnh báo:** "Độ tin cậy OCR thấp"

### Các bước kiểm thử
1. Upload file `scenario3.jpg`
2. ✅ Panel hiện confidence **45%**, 2 thuốc có tên "???" và "Thuốc Y..."
3. ✅ Cảnh báo OCR thấp hiển thị trong panel
4. Gõ **"xác nhận"** (lần 1 — khi chưa sửa)
5. ✅ Bot **CHẶN**: "Còn 2 thuốc chưa được nhận dạng rõ ràng. Vui lòng nhấn 'Sửa'..."
6. ✅ Quick replies: **["Có sai tên thuốc", "Sửa thuốc khác"]**
7. Nhấn nút **"Sửa"** trên thuốc "??? (Thuốc X...)"
8. Nhập tên đúng (ví dụ: **"Ibuprofen"**) → nhấn Lưu
9. ✅ Thuốc đổi tên, confidence nhảy lên **99%**
10. Nhấn nút **"Sửa"** trên thuốc "Thuốc Y (không đọc được)"
11. Nhập tên đúng (ví dụ: **"Vitamin B6"**) → nhấn Lưu
12. ✅ Thuốc đổi tên, confidence nhảy lên **99%**
13. Gõ **"xác nhận"** (lần 2 — sau khi sửa đủ)
14. ✅ Xác nhận **thành công**
15. Gõ "tác dụng phụ" → bot trả lời bình thường
16. ✅ Chat hoạt động tự do

### Kết quả mong đợi
- Lần xác nhận đầu bị chặn khi còn thuốc confidence < 70%
- Sau khi sửa đủ tất cả thuốc mờ → xác nhận thành công
- Chat hoạt động bình thường sau khi xác nhận

---

## Kịch bản 4 — Không đọc được ảnh

### Mục tiêu
Kiểm thử: khi ảnh quá mờ/bị che/không phải đơn thuốc, hệ thống báo lỗi rõ ràng và cho phép upload lại.

### File upload
`scenario4.jpg` (hoặc `khong-doc.jpg`)

### Dữ liệu mock
- `scanPrescription()` ném lỗi ngay sau 900ms:
  > "Không thể nhận diện đơn thuốc. Ảnh quá mờ hoặc bị che khuất. Vui lòng chụp lại và tải lên."

### Các bước kiểm thử
1. Upload file `scenario4.jpg`
2. ✅ Loading spinner hiện trong **~900ms**
3. ✅ **Banner lỗi đỏ** xuất hiện phía trên ô nhập với nội dung đầy đủ
4. ✅ Panel bên phải vẫn hiện trạng thái "Chưa có dữ liệu" (prescription = null)
5. ✅ Nút upload ảnh vẫn hoạt động
6. Upload lại với file **`scenario1.jpg`**
7. ✅ Banner lỗi biến mất
8. ✅ Kịch bản 1 chạy bình thường

### Kết quả mong đợi
- Thông báo lỗi hiển thị rõ ràng, đúng nội dung
- Không có dữ liệu đơn thuốc nào được lưu
- App không crash
- Người dùng có thể thử lại ngay

---

## Ghi chú kỹ thuật

- Routing kịch bản: dựa trên `file.name.toLowerCase().startsWith(...)` trong `mockApi.js`
- Confidence threshold chặn xác nhận: **< 0.70** (sau khi sửa thuốc, mock set = 0.99)
- Scenario 2 blocking: kiểm tra `highRisk` (useMemo trong App.jsx) sau khi `status === 'confirmed'`
- Scenario 4: `runTask()` trong App.jsx bắt lỗi và gọi `setError(err.message)` — không cần thay đổi UI
- File có thể là bất kỳ định dạng nào (jpg, png, pdf) miễn là đổi tên đúng tiền tố
