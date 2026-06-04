from copy import deepcopy


MOCK_PRESCRIPTIONS = [
    {
        "prescriptionId": "rx-demo-0603",
        "confidence": 0.91,
        "doctorName": "BS. Lê Văn C",
        "clinic": "Phòng khám Nội tiết",
        "issuedAt": "2026-06-03",
        "status": "pending",
        "medications": [
            {
                "id": "med-1",
                "name": "Metformin",
                "strength": "500mg",
                "dose": "1 viên",
                "schedule": "Sau ăn sáng và tối",
                "duration": "30 ngày",
                "risk": "normal",
                "confidence": 0.82,
                "notes": "Thường được dùng để hỗ trợ kiểm soát đường huyết theo đơn.",
            },
            {
                "id": "med-2",
                "name": "Atorvastatin",
                "strength": "10mg",
                "dose": "1 viên",
                "schedule": "Tối trước khi ngủ",
                "duration": "30 ngày",
                "risk": "normal",
                "confidence": 0.94,
                "notes": "Thường được dùng để hỗ trợ kiểm soát lipid máu theo đơn.",
            },
            {
                "id": "med-3",
                "name": "Prednisolone",
                "strength": "20mg",
                "dose": "1 viên",
                "schedule": "Sau ăn sáng",
                "duration": "14 ngày",
                "risk": "high",
                "confidence": 0.9,
                "notes": "Cần dùng đúng liều và không tự ý ngừng đột ngột.",
            },
        ],
        "warnings": [
            {
                "id": "warn-1",
                "level": "high",
                "title": "Cần dùng đúng liều",
                "detail": "Prednisolone cần dùng đúng liều trong đơn và không tự ý ngừng đột ngột.",
            }
        ],
    },
    {
        "prescriptionId": "rx-demo-0604",
        "confidence": 0.88,
        "doctorName": "BS. Nguyễn Minh H",
        "clinic": "Phòng khám Hô hấp",
        "issuedAt": "2026-06-04",
        "status": "pending",
        "medications": [
            {
                "id": "med-1",
                "name": "Amoxicillin",
                "strength": "500mg",
                "dose": "1 viên",
                "schedule": "Sau ăn sáng, trưa và tối",
                "duration": "7 ngày",
                "risk": "normal",
                "confidence": 0.89,
                "notes": "Kháng sinh, cần dùng đủ liệu trình trong đơn.",
            },
            {
                "id": "med-2",
                "name": "Paracetamol",
                "strength": "500mg",
                "dose": "1 viên khi cần",
                "schedule": "Cách nhau ít nhất 6 giờ nếu dùng",
                "duration": "3 ngày",
                "risk": "normal",
                "confidence": 0.93,
                "notes": "Cần tránh dùng quá tổng liều mỗi ngày.",
            },
        ],
        "warnings": [
            {
                "id": "warn-1",
                "level": "medium",
                "title": "Lưu ý tổng liều",
                "detail": "Paracetamol cần được tính tổng liều trong ngày nếu có dùng thêm thuốc khác cùng hoạt chất.",
            }
        ],
    },
    {
        "prescriptionId": "rx-demo-0605",
        "confidence": 0.86,
        "doctorName": "DS. Trần Thu P",
        "clinic": "Nhà thuốc tư vấn",
        "issuedAt": "2026-06-05",
        "status": "pending",
        "medications": [
            {
                "id": "med-1",
                "name": "Omeprazole",
                "strength": "20mg",
                "dose": "1 viên",
                "schedule": "Trước ăn sáng 30 phút",
                "duration": "14 ngày",
                "risk": "normal",
                "confidence": 0.9,
                "notes": "Thường được dùng theo đơn để giảm tiết acid dạ dày.",
            },
            {
                "id": "med-2",
                "name": "Domperidone",
                "strength": "10mg",
                "dose": "1 viên",
                "schedule": "Trước ăn 15-30 phút",
                "duration": "5 ngày",
                "risk": "normal",
                "confidence": 0.84,
                "notes": "Cần dùng theo đúng tần suất trong đơn.",
            },
        ],
        "warnings": [],
    },
]


SPECIALISTS = [
    {
        "id": "sp-1",
        "name": "BS. Phạm Thị Lan",
        "specialty": "Nội tiết",
        "location": "Chat tư vấn trực tuyến",
        "nextSlot": "2026-06-05T09:00:00+07:00",
    },
    {
        "id": "sp-2",
        "name": "DS. Nguyễn Minh Tuấn",
        "specialty": "Tư vấn dược",
        "location": "Chat tư vấn trực tuyến",
        "nextSlot": "2026-06-06T14:00:00+07:00",
    },
]


def initial_prescription_store():
    return {item["prescriptionId"]: deepcopy(item) for item in MOCK_PRESCRIPTIONS}
