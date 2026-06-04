# Thin SPEC — Long Châu AI Đọc Đơn Thuốc

## 1. Track, product/app và user

**Track:** Healthcare / AI Product

**Product/app thật:** Long Châu AI — Chatbot đọc đơn thuốc

**User cụ thể:**  
Bệnh nhân 18–60 tuổi, vừa khám xong tại phòng khám hoặc bệnh viện, không có nền tảng y tế, cầm đơn thuốc có 2–5 loại thuốc và cần hiểu cách dùng trước khi về nhà hoặc trước khi uống thuốc tại nhà.

**Nhóm có phải user thật không? Nếu không, khác ở đâu?**  
Một phần có. Thành viên nhóm có thể đã từng nhận đơn thuốc thông thường như kháng sinh, hạ sốt, thuốc dạ dày và gặp pain này. Tuy nhiên nhóm chưa chắc đại diện cho người dùng có đơn thuốc bệnh nặng/mãn tính như tim mạch, tiểu đường, ung thư, tâm thần. Segment đó cần phỏng vấn thêm và đưa vào failure/risk path.

---

## 2. Evidence summary

| Evidence | Nguồn | User/pain nói lên điều gì? | SPEC phải đổi gì? |
|---|---|---|---|
| Tên thuốc tiếng Latin/viết tắt trên đơn không hiểu, phải tra Google hoặc hỏi dược sĩ. | Self-use / quan sát sau khám. | User không thiếu thông tin, họ thiếu cách dịch thông tin y tế sang ngôn ngữ thường ngày. | Build slice phải có giải thích ngôn ngữ thông thường, không dùng thuật ngữ chuyên môn. |
| Bỏ liều vì không có nhắc nhở. | Self-use / trải nghiệm dùng thuốc nhiều ngày. | Reminder là nhu cầu thực, không phải tính năng phụ. | Reminder nằm trong build slice chính, không đưa hết vào backlog. |
| Medisafe có reminder nhưng user phải nhập tay từng thuốc. | Competitor analysis. | Setup ban đầu friction cao. | OCR đọc đơn là differentiator cốt lõi. |
| Đơn thuốc mờ/chữ viết tay khó đọc. | Self-use / quan sát. | OCR có rủi ro đọc sai. | Bắt buộc có user confirmation và low-confidence path. |

---

## 3. Pain statement

```text
User bệnh nhân vừa khám xong đang gặp khó ở bước đọc và hiểu đơn thuốc,
vì tên thuốc viết tắt/tiếng Latin, liều lượng và thời gian uống được ghi theo format
y tế khó hiểu với người không có nền tảng chuyên môn.
Điều này dẫn tới việc user uống sai cách, bỏ liều không hay biết,
hoặc mất thời gian tự Google/gọi lại bác sĩ để hỏi những câu đơn giản.

Bằng chứng chính là trải nghiệm self-use: nhận đơn sau khám và không đọc được
tên thuốc nếu không tra Google hoặc hỏi dược sĩ.
Quan sát workflow cũng cho thấy sau khi rời phòng khám,
user thường không còn người giải thích đơn thuốc ngay lập tức.
```

---

## 4. Build slice

```text
Cho bệnh nhân vừa nhận đơn thuốc và không hiểu rõ nội dung,
prototype sẽ dùng AI để đọc ảnh đơn thuốc bằng OCR + LLM
và trả lời câu hỏi của người dùng về từng loại thuốc bằng ngôn ngữ thông thường.

Prototype tạo ra:
- danh sách thuốc đã nhận dạng,
- bước user xác nhận tên thuốc,
- giải thích cá nhân hóa theo đúng đơn đó,
- lịch nhắc uống thuốc tự động trước 1h nếu có giờ uống,
- xử lý OCR không chắc hoặc đơn có thuốc nguy hiểm bằng cách yêu cầu user xác nhận,
  chụp lại hoặc gợi ý hỏi dược sĩ/bác sĩ.
```

---

## 5. Auto/Aug decision

Chọn:

- [ ] **Augmentation:** AI gợi ý/draft/phân loại, user quyết cuối.
- [x] **Conditional automation:** AI tự làm trong case hẹp; case mơ hồ/rủi ro chuyển người.
- [ ] **Automation:** AI tự quyết và tự hành động.

**Lý do chọn:**  
AI có thể tự động hóa các bước hẹp như OCR, parse đơn thuốc, tóm tắt công dụng, tạo reminder. Nhưng trong lĩnh vực y tế, AI không được tự quyết định ở các tình huống rủi ro: OCR confidence thấp, tên thuốc lạ hoặc không chắc, thuốc nguy hiểm, user hỏi về đổi liều/ngưng thuốc, hoặc có bệnh nền/phụ nữ mang thai/trẻ em/người già. Vì vậy chọn conditional automation.

**Human role:**  
- **User là decider đầu tiên:** xác nhận tên thuốc trước khi AI giải thích.  
- **Dược sĩ/bác sĩ là rescuer:** xử lý các case nguy hiểm, không chắc hoặc cần tư vấn chuyên môn.  
- **AI là assistant:** đọc, giải thích, nhắc nhở, nhưng không thay thế chuyên gia y tế.

---

## 6. Four paths

| Path | Prototype phải thể hiện gì? |
|---|---|
| Happy | Upload ảnh đơn rõ nét → OCR confidence ≥ 80% → user xác nhận danh sách thuốc → AI giải thích từng thuốc → phát hiện lịch uống → đề nghị tạo reminder → tạo reminder → tóm tắt đơn thuốc. |
| Low-confidence | Upload ảnh mờ/chữ viết tay → OCR confidence < 80% → AI yêu cầu user chụp lại hoặc nhập tay → user nhập tên thuốc → AI cập nhật và tiếp tục giải thích. |
| Failure | OCR confidence 82% nhưng đọc sai "Metronidazole" thay vì "Metformin" → user phát hiện và sửa → AI cập nhật và giải thích đúng thuốc. |
| Correction | User đã xác nhận đơn và AI tạo reminder 8h sáng → user yêu cầu đổi sang 9h vì thức dậy muộn → AI cập nhật reminder theo yêu cầu và hiển thị lịch mới để xác nhận. |

---

## 7. Failure mode nguy hiểm nhất

```text
Trigger:
User tin tưởng hoàn toàn vào kết quả AI mà không kiểm tra lại tên thuốc.

Failure:
OCR đọc nhầm "Metformin 500mg" thành "Metronidazole 500mg".

Impact:
Hai thuốc có công dụng khác nhau.
User có thể hiểu sai thuốc, uống sai thuốc, bỏ lỡ điều trị bệnh chính
hoặc gặp tác dụng phụ không mong muốn.

Mitigation:
1. Bước xác nhận bắt buộc:
   AI không bao giờ bắt đầu giải thích trước khi user xác nhận danh sách thuốc.
2. Hiển thị tên thuốc to, rõ, dạng card để user so sánh với đơn gốc.
3. Nếu confidence thấp hoặc tên thuốc thuộc nhóm nguy hiểm:
   yêu cầu chụp lại/nhập tay hoặc chuyển sang dược sĩ.
4. Disclaimer cố định:
   "Thông tin chỉ mang tính tham khảo. Hãy xác nhận với bác sĩ/dược sĩ
   trước khi thay đổi cách dùng thuốc."

Owner kiểm thử path này là thành viên phụ trách Test / failure path.
```

---

## 8. Owner plan cho sáng Day 06

| Thành viên | Việc phụ trách | Bằng chứng cần có trong repo |
|---|---|---|
| Product owner | Chốt scope MVP, giữ flow không bị rộng quá. | File SPEC cuối cùng + câu chốt build slice. |
| Research / evidence | Phỏng vấn nhanh 3 user/bệnh nhân, bổ sung evidence thật. | Evidence pack có quote/observation rõ. |
| UX/UI | Thiết kế màn upload đơn, xác nhận thuốc, chatbot, reminder, warning. | Wireframe hoặc screenshot prototype. |
| AI/Backend | Làm OCR/mock OCR, parse thuốc, LLM response, confidence check. | API chạy được happy path end-to-end. |
| Frontend | Build flow demo 3–5 phút. | App demo chạy được trên local. |
| Test / failure path | Test ảnh mờ, OCR sai Metformin/Metronidazole, thuốc nguy hiểm. | Test log hoặc markdown ghi lại failure handling. |
| Demo/repo | Viết README, demo script, hướng dẫn chạy. | README.md + link demo/video nếu có. |

---

## 9. Success metrics

### Metric cho prototype

- User hiểu công dụng thuốc sau dưới 1 phút.
- User xác nhận được danh sách thuốc trước khi AI giải thích.
- User tạo được reminder trong flow.
- AI xử lý được ít nhất 1 low-confidence case.
- AI xử lý được ít nhất 1 failure case OCR sai tên thuốc.

### Metric nếu triển khai thật

- Giảm thời gian user tra cứu đơn thuốc.
- Tăng tỷ lệ user uống thuốc đúng giờ.
- Giảm số lần user phải tự Google từng tên thuốc.
- Tăng tỷ lệ user hỏi dược sĩ trong case nguy hiểm.
- Giảm rủi ro AI trả lời khi không đủ tự tin.

---

## 10. Demo script 3–5 phút

1. Mở app Long Châu AI.
2. Chọn "Hỏi về đơn thuốc".
3. Upload ảnh đơn thuốc mẫu có 3 thuốc.
4. AI đọc ra danh sách:
   - Amoxicillin 500mg
   - Omeprazole 20mg
   - Paracetamol 500mg
5. User xác nhận danh sách thuốc.
6. User hỏi: "Omeprazole uống lúc nào?"
7. AI trả lời ngắn gọn, dễ hiểu.
8. AI đề xuất tạo reminder:
   "Bạn có muốn mình nhắc uống thuốc trước 1h không?"
9. User đồng ý.
10. App hiển thị tóm tắt đơn thuốc + reminder đã tạo.
11. Chuyển qua failure demo:
    AI đọc nhầm Metformin thành Metronidazole.
12. User sửa lại.
13. AI cập nhật và giải thích lại đúng thuốc.

---

## 11. MVP scope

### Có trong MVP Day 06

- Upload/chụp ảnh đơn thuốc mẫu.
- OCR hoặc mock OCR từ ảnh đơn thuốc.
- Parse danh sách thuốc.
- User xác nhận/sửa danh sách thuốc.
- AI giải thích công dụng từng thuốc bằng ngôn ngữ dễ hiểu.
- Q&A đơn giản theo đơn thuốc.
- Tạo reminder uống thuốc trước 1h.
- Low-confidence path.
- Failure path OCR đọc nhầm tên thuốc.
- Disclaimer y tế.
- Nút "Hỏi dược sĩ" hoặc mock escalation.

### Không có trong MVP Day 06

- Database thuốc Việt Nam đầy đủ.
- Nhận dạng chữ viết tay bác sĩ ở độ chính xác cao.
- Kiểm tra tương tác thuốc chuyên sâu.
- Cá nhân hóa theo bệnh nền/dị ứng.
- Tự động mua thuốc.
- Chẩn đoán bệnh.
- Thay đổi liều/ngưng thuốc.
- Kết nối thật với hệ thống bác sĩ/bệnh viện.
- Hỗ trợ nhiều ngôn ngữ.
- Lịch sử đơn thuốc dài hạn.

---

## Backlog

Những thứ **không build trong Day 06**:

- Database thuốc Việt Nam đầy đủ.
- Nhận dạng chữ viết tay bác sĩ chuyên sâu.
- Kiểm tra tương tác thuốc phức tạp.
- Cá nhân hóa theo hồ sơ bệnh án, dị ứng, bệnh nền.
- Lưu lịch sử đơn thuốc theo thời gian.
- Kết nối trực tiếp với dược sĩ Long Châu thật.
- Kết nối booking bác sĩ/bệnh viện thật.
- Tự động đặt mua thuốc từ đơn.
- Hỗ trợ đa ngôn ngữ.
- Dashboard cho dược sĩ review ca nguy hiểm.
- Tích hợp bảo hiểm/y bạ điện tử.
- Kiểm chứng lâm sàng câu trả lời AI.

---

## Product decision

Long Châu nên triển khai chatbot AI đọc đơn thuốc theo hướng **conditional automation + human safety check**. AI có thể tự động đọc đơn, giải thích và tạo nhắc uống thuốc trong case hẹp, nhưng không được tự chẩn đoán, không đổi liều, không khuyên ngưng thuốc và không thay thế dược sĩ/bác sĩ. Khi AI không chắc, OCR sai, ảnh mờ, thuốc nguy hiểm hoặc user hỏi câu hỏi y tế nhạy cảm, hệ thống phải chuyển sang dược sĩ/bác sĩ hoặc yêu cầu user xác nhận lại.
