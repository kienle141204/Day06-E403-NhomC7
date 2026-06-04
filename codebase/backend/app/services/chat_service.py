"""Chat service for deterministic medication question answering."""
import re
import logging
from typing import Optional

from app.services.prescription_store import get_prescription
from app.services.analysis_service import analyze_prescription
from app.services.safety_service import SAFETY_NOTICE

logger = logging.getLogger(__name__)

INTENTS = {
    "uses": ["cong dung", "dung de lam gi", "tac dung", "co tac dung gi", "chi co tac dung", "lam gi"],
    "drowsiness": ["buon ngu", "lai xe", "choang", "met", "drowsiness", "nga", "chong mat"],
    "antibiotic": ["khang sinh", "antibiotic"],
    "schedule": ["lich", "ngay may lan", "truoc an", "sau an", "gio uong", "luc nao uong"],
    "dose_change": ["tang lieu", "giam lieu", "gap doi", "ngung", "bo thuoc", "doi thuoc", "thay thuoc", "tang giam", "them thuoc", "bot thuoc", "gap doi", "them lieu", "bot lieu"],
    "interaction": ["tuong tac", "uong chung", "ruou", "bia"],
}

VIETNAMESE_MAP = {
    'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
    'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
    'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
    'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
    'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
    'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
    'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
    'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
    'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
    'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
    'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
    'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    'đ': 'd',
}


def _to_ascii(text: str) -> str:
    """Convert Vietnamese text to ASCII by replacing accented characters."""
    result = []
    for char in text:
        result.append(VIETNAMESE_MAP.get(char, char))
    return ''.join(result)


def _normalize_question(text: str) -> str:
    """Normalize Vietnamese text: to ASCII, lowercase, collapse spaces."""
    if not text:
        return ""
    text = _to_ascii(text)
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = " ".join(text.split())
    return text


def _normalize_for_match(text: str) -> str:
    """Normalize text for matching (to ASCII, lowercase)."""
    if not text:
        return ""
    text = _to_ascii(text)
    text = text.lower()
    return text


def _detect_intent(question: str) -> str:
    """Detect intent from normalized question."""
    normalized = _normalize_question(question)
    for intent, keywords in INTENTS.items():
        for kw in keywords:
            if kw in normalized:
                return intent
    return "general"


def _get_medications_from_prescription(prescription_id: str) -> tuple[list, str]:
    """
    Get resolved medications from prescription.
    Returns (medications, error_message)
    """
    prescription = get_prescription(prescription_id)
    if not prescription:
        return [], "Không tìm thấy đơn thuốc."

    status = prescription.get("status", "")
    analysis = prescription.get("analysis")

    if not analysis:
        if status == "confirmed":
            try:
                analysis = analyze_prescription(prescription_id)
            except ValueError:
                return [], "Đơn thuốc chưa được phân tích."
        else:
            return [], "Đơn thuốc chưa được xác nhận hoặc phân tích."

    medications = analysis.get("medications", [])
    if not medications:
        return [], "Không có thuốc nào trong đơn."

    return medications, ""


def _build_uses_answer(medications: list) -> tuple[str, list]:
    """Build answer for uses intent."""
    related = []
    lines = ["Công dụng của các thuốc trong đơn:"]

    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        uses = med.get("uses_vi", [])
        found = med.get("found", True)

        related.append(name)

        if not found:
            lines.append(f"• {name}: Chưa tìm thấy thông tin trong cơ sở dữ liệu, cần hỏi dược sĩ/bác sĩ.")
        elif uses and isinstance(uses, list) and any(u for u in uses if u):
            use_text = "; ".join(u for u in uses if u)
            lines.append(f"• {name}: {use_text}")
        else:
            lines.append(f"• {name}: Chưa có đủ dữ liệu công dụng, cần hỏi dược sĩ/bác sĩ.")

    return "\n".join(lines), related


def _build_drowsiness_answer(medications: list) -> tuple[str, list]:
    """Build answer for drowsiness/side effects intent."""
    related = []
    lines = ["Các thuốc có thể gây buồn ngủ hoặc chóng mặt:"]

    found_any = False
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        category = _normalize_for_match(med.get("category_vi", "") or "")
        notes = med.get("important_notes_vi", []) or []
        notes_text = _normalize_for_match(" ".join(notes))

        is_drowsy = (
            "khang histamin" in category
            or "chong di ung" in category
            or "khang histamine" in category
            or "buon ngu" in notes_text
            or "chong mat" in notes_text
            or "lai xe" in notes_text
            or "nga" in notes_text
        )

        if is_drowsy:
            found_any = True
            related.append(name)
            if notes and any(n for n in notes if n):
                lines.append(f"• {name}: {'; '.join(n for n in notes if n)}")
            else:
                lines.append(f"• {name}: Thuốc có thể gây buồn ngủ nhẹ.")

    if not found_any:
        lines.append("Trong dữ liệu hiện tại, mình chưa thấy thuốc nào có ghi chú rõ về buồn ngủ.")
        lines.append("Tuy nhiên nếu bạn thấy buồn ngủ/chóng mặt, nên tránh lái xe và hỏi dược sĩ/bác sĩ.")

    return "\n".join(lines), related


def _build_antibiotic_answer(medications: list) -> tuple[str, list]:
    """Build answer for antibiotic intent."""
    related = []
    lines = ["Các thuốc kháng sinh trong đơn:"]

    found_any = False
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        category_orig = med.get("category_vi", "") or ""
        category = _normalize_for_match(category_orig)
        ingredient = _normalize_for_match(med.get("ingredient_vi", "") or "")

        is_antibiotic = (
            "khang sinh" in category
            or "khang sinh" in ingredient
            or "amoxicillin" in ingredient
            or "azithromycin" in ingredient
            or "ciprofloxacin" in ingredient
            or "metronidazole" in ingredient
            or "cephalosporin" in category
        )

        if is_antibiotic:
            found_any = True
            related.append(name)
            if category_orig:
                lines.append(f"• {name} ({category_orig})")
            else:
                lines.append(f"• {name}")

    if not found_any:
        lines.append("Không có thuốc kháng sinh nào trong đơn này.")
    else:
        lines.append("")
        lines.append("Lưu ý: Không tự ý ngưng kháng sinh giữa chừng nếu chưa hỏi bác sĩ.")

    return "\n".join(lines), related


def _build_schedule_answer(medications: list) -> tuple[str, list]:
    """Build answer for schedule intent."""
    related = []
    lines = ["Lịch uống thuốc theo đơn đã xác nhận:"]

    found_any = False
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        dosage = med.get("dosage") or med.get("dose") or "1 viên"
        frequency = med.get("frequency") or med.get("schedule") or ""
        duration = med.get("duration") or ""

        related.append(name)
        found_any = True

        schedule_parts = [dosage]
        if frequency:
            schedule_parts.append(frequency)
        if duration:
            schedule_parts.append(f"trong {duration}")

        lines.append(f"• {name}: {', '.join(schedule_parts)}")

    if not found_any:
        lines.append("Không có thông tin lịch uống trong đơn.")

    notes = []
    for med in medications:
        notes_text = _normalize_for_match(" ".join(med.get("important_notes_vi", []) or []))
        if "truoc an" not in notes_text and "sau an" not in notes_text:
            notes.append(med.get("raw_name") or med.get("name", ""))

    if notes:
        lines.append("")
        lines.append("Đơn hiện chưa ghi rõ trước hay sau ăn; bạn nên theo hướng dẫn bác sĩ/dược sĩ hoặc tờ hướng dẫn thuốc.")

    return "\n".join(lines), related


def _build_interaction_answer(medications: list) -> tuple[str, list]:
    """Build answer for drug interaction intent."""
    related = []
    lines = ["Về tương tác thuốc trong đơn:"]

    high_risk_meds = []
    for med in medications:
        risk = med.get("risk_level", "low")
        name = med.get("raw_name") or med.get("name", "Unknown")
        if risk == "high":
            high_risk_meds.append(name)
            related.append(name)

    if high_risk_meds:
        lines.append(f"Các thuốc cần lưu ý: {', '.join(high_risk_meds)}")
    else:
        lines.append("Chưa phát hiện thuốc nguy cơ cao trong đơn.")

    lines.append("")
    lines.append("Mình chưa có đủ dữ liệu để khẳng định tương tác thuốc đầy đủ.")
    lines.append("Hãy hỏi dược sĩ/bác sĩ để được tư vấn chính xác về các thuốc dùng chung.")

    return "\n".join(lines), related


def _build_general_answer(medications: list) -> tuple[str, list]:
    """Build answer for general intent."""
    related = []
    lines = ["Tóm tắt các thuốc trong đơn đã xác nhận:"]

    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        related.append(name)
        category = med.get("category_vi", "")
        if category:
            lines.append(f"• {name} ({category})")
        else:
            lines.append(f"• {name}")

    lines.append("")
    lines.append("Bạn có thể hỏi tôi về:")
    lines.append("• Công dụng của từng thuốc")
    lines.append("• Thuốc nào là kháng sinh")
    lines.append("• Thuốc nào dễ gây buồn ngủ")
    lines.append("• Lịch uống theo đơn")

    return "\n".join(lines), related


def answer_question(prescription_id: str, question: str) -> dict:
    """
    Answer medication question deterministically.

    Args:
        prescription_id: ID of the confirmed prescription
        question: User's question in Vietnamese

    Returns:
        dict with answer, risk_level, intent, related_medications, safety_notice
    """
    logger.info(f"[CHAT] prescription_id={prescription_id}, question='{question}'")

    medications, error = _get_medications_from_prescription(prescription_id)
    if error:
        logger.warning(f"[CHAT] Error: {error}")
        return {
            "answer": error + " Vui lòng bắt đầu lại.",
            "risk_level": "low",
            "intent": "error",
            "related_medications": [],
            "safety_notice": SAFETY_NOTICE
        }

    intent = _detect_intent(question)
    logger.info(f"[CHAT] detected intent={intent}, medications_count={len(medications)}")

    if intent == "uses":
        answer, related = _build_uses_answer(medications)
        risk_level = "low"
    elif intent == "drowsiness":
        answer, related = _build_drowsiness_answer(medications)
        risk_level = "medium"
    elif intent == "antibiotic":
        answer, related = _build_antibiotic_answer(medications)
        risk_level = "medium"
    elif intent == "schedule":
        answer, related = _build_schedule_answer(medications)
        risk_level = "low"
    elif intent == "dose_change":
        answer = (
            "Bạn không nên tự ý tăng/giảm liều, ngưng thuốc hoặc thay thuốc. "
            "Hãy dùng đúng theo đơn đã được kê. "
            "Nếu có tác dụng phụ hoặc muốn đổi thuốc, bạn cần hỏi bác sĩ/dược sĩ."
        )
        related = [m.get("raw_name") or m.get("name", "") for m in medications]
        risk_level = "high"
    elif intent == "interaction":
        answer, related = _build_interaction_answer(medications)
        risk_level = "medium"
    else:
        answer, related = _build_general_answer(medications)
        risk_level = "low"

    logger.info(f"[CHAT] related_medications={related}, risk_level={risk_level}")

    return {
        "answer": answer,
        "risk_level": risk_level,
        "intent": intent,
        "related_medications": related,
        "safety_notice": SAFETY_NOTICE
    }
