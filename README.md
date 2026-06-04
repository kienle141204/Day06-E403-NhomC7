# MedChat — Dược sĩ AI tư vấn đơn thuốc

> **Day06 · E403 · Nhóm C7** — AI Product Hackathon, Batch 02

---

## Thành viên nhóm

| Mã học viên | Họ và tên |
|-------------|-----------|
| 2A202600834 | Lê Trung Kiên |
| 2A202600809 | Lê Vũ Anh |
| 2A202600717 | Đỗ Thị Thanh Bình |

---

## Phân công công việc

| Thành viên | Phần phụ trách |
|------------|----------------|
| Lê Trung Kiên | AI agent (LLM Q&A, safety logic, OCR pipeline) · Frontend (chat interface, luồng xác nhận thuốc) · Workflow & kiểm thử |
| Lê Vũ Anh | AI agent (prompt engineering, xử lý response) · SPEC sản phẩm · Workflow & kiểm thử |
| Đỗ Thị Thanh Bình | Frontend (giao diện upload ảnh, màn hình danh sách thuốc) · SPEC sản phẩm · Workflow & kiểm thử |

---

## Mô tả sản phẩm

**MedChat** là trợ lý AI chủ động cho bệnh nhân sau khi khám — không chỉ giải thích đơn thuốc mà còn tự động tạo lịch nhắc uống thuốc đúng giờ và kết nối bác sĩ/dược sĩ ngay khi phát hiện nguy cơ từ đơn.

**Điểm khác biệt cốt lõi:**
- AI phân tích toàn bộ đơn thuốc và **tự sinh lịch nhắc uống thuốc** (sáng/trưa/chiều/tối, trước/sau ăn) — không cần người dùng tự nhập tay.
- Khi phát hiện tương tác thuốc nguy hiểm hoặc liều cao bất thường, AI **chủ động đề xuất đặt lịch gặp bác sĩ** ngay trong chat, không đợi người dùng hỏi.

**Luồng sử dụng:**

1. Người dùng chụp ảnh / upload đơn thuốc
2. AI đọc và trích xuất danh sách thuốc (OCR)
3. Người dùng kiểm tra và xác nhận tên thuốc
4. AI tự động phân tích đơn — sinh lịch nhắc uống thuốc chi tiết cho từng loại
5. Hỏi đáp tự do: công dụng, tác dụng phụ, chống chỉ định
6. Nếu phát hiện rủi ro: AI chủ động kết nối bác sĩ / đặt lịch tư vấn

**Track:** Healthcare — lấy cảm hứng từ Long Châu, Pharmacity, Vinmec

---

## Cấu trúc repo

```
Day06-E403-NhomC7/
├── README.md                        ← File này
├── workflow.md                      ← Luồng xử lý an toàn của chatbot
├── spec/
│   ├── README.md                    ← Hướng dẫn SPEC
│   ├── product-canvas.md            ← Product Canvas (painpoint, solution, target user)
│   ├── user-stories.md              ← User stories & acceptance criteria
│   └── wireframes/                  ← Mockup giao diện
└── codebase/
    ├── README.md                    ← Hướng dẫn chạy & deploy
    ├── frontend/                    ← React 19 + Vite
    │   ├── src/
    │   │   ├── App.jsx              ← Toàn bộ UI & state (upload, chat, reminder)
    │   │   ├── api/
    │   │   │   └── client.js        ← API adapter (mock ↔ real backend)
    │   │   └── data/
    │   │       └── mockApi.js       ← Mock API với dữ liệu mẫu 3 thuốc
    │   ├── index.html
    │   └── package.json
    ├── backend/                     ← Placeholder (chưa implement)
```

---

## Kịch bản kiểm thử

### Kịch bản 1 — Đơn thuốc rõ ràng: đặt lời nhắc và chat
**Đầu vào:** Ảnh đơn thuốc chụp rõ, OCR trích xuất đủ tên thuốc và liều lượng.  
**Luồng:** Người dùng xác nhận danh sách thuốc → AI tự sinh lịch nhắc uống thuốc cho từng loại (sáng/tối, trước/sau ăn) → người dùng hỏi thêm về công dụng, tác dụng phụ qua chat.  
**Kết quả kỳ vọng:** Lịch nhắc được tạo đúng theo chỉ định trên đơn; chatbot trả lời chính xác các câu hỏi liên quan đến thuốc đã xác nhận.

---

### Kịch bản 2 — Đơn thuốc mờ: yêu cầu người dùng sửa trước khi tiếp tục
**Đầu vào:** Ảnh đơn thuốc chụp thiếu sáng hoặc bị mờ, OCR trả về tên thuốc hoặc liều lượng có độ tin cậy thấp (<80%).  
**Luồng:** AI đánh dấu các trường nghi ngờ và hiển thị form chỉnh sửa → người dùng sửa tên thuốc / liều lượng → xác nhận lại → tiếp tục luồng bình thường.  
**Kết quả kỳ vọng:** Chatbot không giải thích thuốc nào cho đến khi toàn bộ thông tin đã được người dùng xác nhận; không có lịch nhắc nào được tạo trước bước này.

---

### Kịch bản 3 — Câu hỏi ngoài phạm vi: chatbot từ chối lịch sự
**Đầu vào:** Người dùng đặt câu hỏi không liên quan đến đơn thuốc hoặc sức khỏe (ví dụ: hỏi thời tiết, nấu ăn, tin tức).  
**Luồng:** Chatbot nhận diện câu hỏi ngoài phạm vi → từ chối nhẹ nhàng, nhắc lại phạm vi hỗ trợ (tư vấn thuốc trong đơn) → gợi ý người dùng quay lại hỏi về đơn thuốc.  
**Kết quả kỳ vọng:** Không có câu trả lời sai lệch hoặc bịa đặt; chatbot không bị dẫn dắt ra ngoài chủ đề y tế.

---

### Kịch bản 4 — Thuốc nguy hiểm / rủi ro cao: chủ động gợi ý gặp bác sĩ
**Đầu vào:** Đơn thuốc chứa thuốc có nguy cơ tương tác cao, liều vượt ngưỡng thông thường, hoặc người dùng hỏi về cách dùng thuốc kiểm soát đặc biệt (corticosteroid liều cao, thuốc kháng đông…).  
**Luồng:** AI phát hiện rủi ro → hiển thị cảnh báo rõ ràng → chủ động đề xuất đặt lịch tư vấn với bác sĩ / dược sĩ ngay trong giao diện chat → cung cấp nút đặt lịch nhanh.  
**Kết quả kỳ vọng:** Chatbot không tự ý hướng dẫn điều chỉnh liều; luôn chuyển hướng sang chuyên gia y tế khi vượt quá phạm vi an toàn của chatbot.
