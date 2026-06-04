"""Safety classification service for medications."""
from typing import List

HIGH_RISK_KEYWORDS = [
    # Opioids và giảm đau mạnh — nguy cơ ức chế hô hấp, phụ thuộc
    "opioid",
    "tramadol",
    "morphine",
    "codeine",
    "fentanyl",
    # Gây quái thai — cấm tuyệt đối khi mang thai
    "isotretinoin",
    "acitretin",
    "retinoid",
    "thalidomide",
    # Chỉ số điều trị hẹp — quá liều gây chết người
    "methotrexate",
    "colchicine",
    "digoxin",
    "warfarin",
    "lithium",
    # Thuốc độc tế bào / hóa trị
    "cyclophosphamide",
    "vincristine",
    "bleomycin",
]

MEDIUM_RISK_KEYWORDS = [
    # Cần theo dõi nhưng phổ biến, không trực tiếp nguy hiểm tính mạng
    "corticosteroid",
    "kháng sinh",
    "chống chỉ định",
    "thận",
    "gan",
    "tim",
    "potassium chloride",
    "kali chloride",
]

SAFETY_NOTICE = (
    "Thông tin chỉ mang tính tham khảo, không thay thế tư vấn của bác sĩ/dược sĩ. "
    "Không tự ý thay đổi liều, ngưng thuốc hoặc dùng thuốc kê đơn khi chưa có chỉ định."
)


def classify_risk(resolved_med: dict) -> tuple[str, List[str]]:
    """
    Classify risk level for a medication.
    
    Returns: (risk_level, safety_flags)
    """
    safety_flags: List[str] = []
    risk_level = "low"
    
    category_vi = resolved_med.get("category_vi", "") or ""
    ingredient_vi = resolved_med.get("ingredient_vi", "") or ""
    important_notes = resolved_med.get("important_notes_vi", []) or []
    needs_review = resolved_med.get("needs_review", False)
    confidence = resolved_med.get("confidence", 1.0)
    
    notes_text = " ".join(important_notes).lower()
    
    # Check high risk
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword.lower() in category_vi.lower() or keyword.lower() in ingredient_vi.lower():
            risk_level = "high"
            safety_flags.append(f"Cần thận trọng: {keyword}")
            break
    
    # Check medium risk indicators
    if risk_level == "low":
        for keyword in MEDIUM_RISK_KEYWORDS:
            if keyword.lower() in notes_text or keyword.lower() in category_vi.lower():
                risk_level = "medium"
                safety_flags.append(f"Có thông tin cần lưu ý về {keyword}")
                break
    
    # If needs_review or low confidence, upgrade to at least medium
    if risk_level == "low" and (needs_review or confidence < 0.75):
        risk_level = "medium"
        if not safety_flags:
            safety_flags.append("Cần xác minh thông tin thuốc")
    
    return risk_level, safety_flags


def get_safety_notice() -> str:
    """Get global safety notice."""
    return SAFETY_NOTICE
