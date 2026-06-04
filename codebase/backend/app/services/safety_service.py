"""Safety classification and dangerous request detection for medications."""
import re
from typing import List, Tuple

from .text_utils import normalize_text

HIGH_RISK_KEYWORDS = [
    "kháng sinh",
    "corticosteroid",
    "retinoid",
    "tramadol",
    "opioid",
    "methotrexate",
    "isotretinoin",
    "acitretin",
    "colchicine",
    "potassium chloride",
    "kali"
]

MEDIUM_RISK_KEYWORDS = [
    "chống chỉ định",
    "thận",
    "gan",
    "tim"
]

DANGEROUS_REQUEST_PATTERNS = [
    r"\bchan doan\b",
    r"\bbenh gi\b",
    r"\bco bi\b",
    r"\btu dieu tri\b",
    r"\bdieu tri thay\b",
    r"\bdoi thuoc\b",
    r"\bngung thuoc\b",
    r"\bbo thuoc\b",
    r"\btang lieu\b",
    r"\bgiam lieu\b",
    r"\buong them\b",
    r"\bthem thuoc\b",
    r"\bthay lieu\b",
    r"\bthay doi lieu\b",
    r"\bco nen ngung\b",
    r"\bco nen bo\b",
    r"\bco nen tang\b",
    r"\bco nen giam\b",
    r"\bdoctor\b",
]

SAFETY_NOTICE = (
    "Thông tin chỉ mang tính tham khảo, không thay thế tư vấn của bác sĩ/dược sĩ. "
    "Không tự ý thay đổi liều, ngưng thuốc hoặc dùng thuốc kê đơn khi chưa có chỉ định."
)


def is_dangerous_request(message: str) -> bool:
    """Check if the user's question crosses a safety boundary."""
    normalized = normalize_text(message)
    return any(re.search(pattern, normalized) for pattern in DANGEROUS_REQUEST_PATTERNS)


def classify_risk(resolved_med: dict) -> Tuple[str, List[str]]:
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

    for keyword in HIGH_RISK_KEYWORDS:
        if keyword.lower() in category_vi.lower() or keyword.lower() in ingredient_vi.lower():
            risk_level = "high"
            safety_flags.append(f"Cần thận trọng: {keyword}")
            break

    if risk_level == "low":
        for keyword in MEDIUM_RISK_KEYWORDS:
            if keyword.lower() in notes_text or keyword.lower() in category_vi.lower():
                risk_level = "medium"
                safety_flags.append(f"Có thông tin cần lưu ý về {keyword}")
                break

    if risk_level == "low" and (needs_review or confidence < 0.75):
        risk_level = "medium"
        if not safety_flags:
            safety_flags.append("Cần xác minh thông tin thuốc")

    return risk_level, safety_flags


def get_safety_notice() -> str:
    """Get global safety notice."""
    return SAFETY_NOTICE
