# Codebase — MedChat

## Cách chạy prototype

**Yêu cầu:** Node.js 18+

```bash
cd frontend
npm install
npm run dev
```

Mở trình duyệt tại `http://localhost:5173`.

Prototype chạy hoàn toàn trên frontend với mock API — không cần backend hay API key.

### Build production

```bash
npm run build    # Output vào frontend/dist/
npm run preview  # Preview bản build
```

### Biến môi trường (tuỳ chọn)

| Biến | Mô tả |
|------|-------|
| `VITE_API_BASE_URL` | URL backend thật. Mặc định là `http://localhost:8000`. |
| `VITE_USE_MOCK` | Đặt `true` nếu muốn ép frontend dùng mock API. |

Tạo file `frontend/.env` nếu cần:
```
VITE_API_BASE_URL=http://localhost:8000
```

---

## Công nghệ sử dụng

| Công nghệ | Vai trò |
|-----------|---------|
| React 19 + Vite 7 | Framework frontend |
| Tailwind CSS v4 | Styling |
| Lucide React | Icon library |
| Be Vietnam Pro | Font chữ tiếng Việt |
| Mock API (built-in) | Giả lập OCR + AI chat + đặt lịch |

**Tích hợp AI dự kiến (backend):**
- OCR đơn thuốc: Google Vision API / Azure Form Recognizer
- Q&A chatbot: Claude API (`claude-sonnet-4-6`)
- Kiểm tra tương tác thuốc: DrugBank API

---

## Kiểm thử 4 kịch bản

Xem chi tiết tại [`scenarios/test-scenarios.md`](scenarios/test-scenarios.md).

Upload bất kỳ ảnh nào và đổi tên file để chọn kịch bản:

| Tên file | Kịch bản |
|----------|----------|
| `scenario1.jpg` | Đơn thuốc đơn giản — chat tự do |
| `scenario2.jpg` | Đơn thuốc nguy hiểm — chatbot chặn, hướng đặt lịch |
| `scenario3.jpg` | Đơn không rõ ràng — phải sửa tên thuốc trước |
| `scenario4.jpg` | Ảnh không đọc được — yêu cầu upload lại |

---

## Phân công công việc

| Thành viên | Phần đóng góp |
|------------|---------------|
| [Họ tên]   | [Mô tả phần làm] |
| [Họ tên]   | [Mô tả phần làm] |
| [Họ tên]   | [Mô tả phần làm] |

---

## Cấu trúc thư mục

```
codebase/
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Toàn bộ UI và logic luồng
│   │   ├── api/client.js    # Adapter chuyển mock ↔ backend thật
│   │   └── data/mockApi.js  # Mock data 4 kịch bản
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── backend/                 # (Placeholder — chưa triển khai)
└── scenarios/
    └── test-scenarios.md    # Tài liệu kiểm thử chi tiết
```
