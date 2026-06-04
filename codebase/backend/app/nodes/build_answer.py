"""Chat node: build the answer based on detected intent."""
import json
import re

from ..prompts import MEDICATION_QUICK_REPLIES
from ..services.safety_service import SAFETY_NOTICE


# ---------------------------------------------------------------------------
# Helpers (ported from chat_service.py)
# ---------------------------------------------------------------------------

_VN_MAP: dict[str, str] = {
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
    return "".join(_VN_MAP.get(c, c) for c in text)


def _norm(text: str) -> str:
    return _to_ascii(text or "").lower()


def _build_uses_answer(medications: list) -> tuple[str, list]:
    related = []
    header = f"Công dụng của {medications[0].get('raw_name') or medications[0].get('name')}:" if len(medications) == 1 else "Công dụng của các thuốc trong đơn:"
    lines = [header]
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        uses = med.get("uses_vi") or []
        related.append(name)
        if not med.get("found"):
            lines.append(f"• {name}: Chưa tìm thấy thông tin, cần hỏi dược sĩ/bác sĩ.")
        elif uses and any(u for u in uses if u):
            lines.append(f"• {name}: {'; '.join(u for u in uses if u)}")
        else:
            lines.append(f"• {name}: Chưa có đủ dữ liệu công dụng, cần hỏi dược sĩ/bác sĩ.")
    return "\n".join(lines), related


def _build_drowsiness_answer(medications: list) -> tuple[str, list]:
    related = []
    lines = ["Các thuốc có thể gây buồn ngủ hoặc chóng mặt:"]
    found_any = False
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        category = _norm(med.get("category_vi") or "")
        notes_text = _norm(" ".join(med.get("important_notes_vi") or []))
        if any(k in category or k in notes_text for k in ["khang histamin", "chong di ung", "buon ngu", "chong mat", "lai xe", "nga"]):
            found_any = True
            related.append(name)
            notes = [n for n in (med.get("important_notes_vi") or []) if n]
            lines.append(f"• {name}: {'; '.join(notes) if notes else 'Thuốc có thể gây buồn ngủ nhẹ.'}")
    if not found_any:
        lines.append("Trong dữ liệu hiện tại chưa thấy thuốc nào ghi chú rõ về buồn ngủ.")
        lines.append("Nếu bạn thấy buồn ngủ/chóng mặt, nên tránh lái xe và hỏi dược sĩ/bác sĩ.")
    return "\n".join(lines), related


def _build_antibiotic_answer(medications: list) -> tuple[str, list]:
    related = []
    lines = ["Các thuốc kháng sinh trong đơn:"]
    found_any = False
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        category = _norm(med.get("category_vi") or "")
        ingredient = _norm(med.get("ingredient_vi") or "")
        if any(k in category or k in ingredient for k in [
            "khang sinh", "amoxicillin", "azithromycin", "ciprofloxacin", "metronidazole", "cephalosporin"
        ]):
            found_any = True
            related.append(name)
            cat_orig = med.get("category_vi") or ""
            lines.append(f"• {name}{f' ({cat_orig})' if cat_orig else ''}")
    if not found_any:
        lines.append("Không có thuốc kháng sinh nào trong đơn này.")
    else:
        lines.extend(["", "Lưu ý: Không tự ý ngưng kháng sinh giữa chừng khi chưa hỏi bác sĩ."])
    return "\n".join(lines), related


def _build_schedule_answer(medications: list) -> tuple[str, list]:
    related = []
    header = f"Lịch uống {medications[0].get('raw_name') or medications[0].get('name')}:" if len(medications) == 1 else "Lịch uống thuốc theo đơn đã xác nhận:"
    lines = [header]
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        dosage = med.get("dosage") or med.get("dose") or "1 viên"
        frequency = med.get("frequency") or med.get("schedule") or ""
        duration = med.get("duration") or ""
        related.append(name)
        parts = [dosage]
        if frequency:
            parts.append(frequency)
        if duration:
            parts.append(f"trong {duration}")
        lines.append(f"• {name}: {', '.join(parts)}")
    if not related:
        lines.append("Không có thông tin lịch uống trong đơn.")
    return "\n".join(lines), related


def _build_side_effects_answer(medications: list) -> tuple[str, list, bool]:
    """
    Build side effects answer from medication data.

    Uses important_notes_vi when available; falls back to risk classification
    (safety_flags, risk_level) so the caller always gets a meaningful answer
    even when detailed side-effects text is not in the local DB.

    Returns: (answer, related_names, needs_llm)
      needs_llm=True only when the drug was not found at all in the local DB,
      meaning we have zero structured info and LLM would give a better answer.
    """
    related = []
    lines = []
    needs_llm = False

    header = (
        f"Tác dụng phụ cần lưu ý của {medications[0].get('raw_name') or medications[0].get('name')}:"
        if len(medications) == 1
        else "Tác dụng phụ cần lưu ý:"
    )
    lines.append(header)

    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        notes = [n for n in (med.get("important_notes_vi") or []) if n]
        flags = [f for f in (med.get("safety_flags") or []) if f]
        risk  = med.get("risk_level", "low")
        related.append(name)

        if notes:
            lines.append(f"• {name}: {'; '.join(notes)}")
        elif flags:
            # Use safety classification as fallback
            lines.append(f"• {name}: {'; '.join(flags)}")
        elif med.get("found"):
            # Found in DB but no side-effects text — give risk-level hint
            risk_label = {"high": "nguy cơ cao", "medium": "cần theo dõi", "low": "nhìn chung an toàn khi dùng đúng liều"}.get(risk, "chưa rõ")
            lines.append(f"• {name}: Cơ sở dữ liệu chưa có chi tiết tác dụng phụ, phân loại {risk_label}. Hỏi dược sĩ/bác sĩ để biết thêm.")
        else:
            # Not found at all → only LLM can help
            needs_llm = True
            lines.append(f"• {name}: Không tìm thấy trong cơ sở dữ liệu nội bộ.")

    if not needs_llm:
        lines.extend(["", "Nếu gặp tác dụng phụ bất thường, hãy ngừng thuốc và liên hệ bác sĩ/dược sĩ ngay."])

    return "\n".join(lines), related, needs_llm


def _build_interaction_answer(medications: list) -> tuple[str, list]:
    related = []
    lines = ["Về tương tác thuốc trong đơn:"]
    high_risk = [m.get("raw_name") or m.get("name", "Unknown") for m in medications if m.get("risk_level") == "high"]
    if high_risk:
        related.extend(high_risk)
        lines.append(f"Các thuốc cần lưu ý: {', '.join(high_risk)}")
    else:
        lines.append("Chưa phát hiện thuốc nguy cơ cao trong đơn.")
    lines.extend(["", "Mình chưa đủ dữ liệu khẳng định tương tác thuốc đầy đủ. Hãy hỏi dược sĩ/bác sĩ."])
    return "\n".join(lines), related


def _build_general_answer(medications: list) -> tuple[str, list]:
    related = []
    lines = ["Tóm tắt các thuốc trong đơn đã xác nhận:"]
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        related.append(name)
        cat = med.get("category_vi") or ""
        lines.append(f"• {name}{f' ({cat})' if cat else ''}")
    lines.extend(["", "Bạn có thể hỏi tôi về:", "• Công dụng", "• Kháng sinh", "• Buồn ngủ", "• Lịch uống"])
    return "\n".join(lines), related


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

async def build_answer(state: dict) -> dict:
    """
    Route to the right answer builder based on state['intent'].

    When 'mentioned_drug' is set (user asked about a specific drug), the builder
    receives only that one medication instead of the full list — preventing repeated
    identical answers across turns.

    Falls back to LLM (agent.answer_medication_question) when intent='llm_fallback'.
    Returns state with answer, quick_replies, risk_level, related_medications.
    """
    # Already answered (dangerous request path)
    if state.get("is_dangerous"):
        return state

    intent = state.get("intent", "llm_fallback")
    all_medications = state.get("medications", [])

    # Narrow scope to the specific drug if user named one
    mentioned = state.get("mentioned_drug")
    medications = [mentioned] if mentioned else all_medications

    def _build_drug_context(drug: dict | None, all_meds: list) -> str | None:
        """
        Format internal DB data for a specific drug (or all meds) as a
        readable string the LLM can use to give precise answers.
        """
        targets = [drug] if drug else all_meds
        if not targets:
            return None

        entries = []
        for med in targets:
            entry = {
                "ten_thuoc": med.get("raw_name") or med.get("name"),
                "hoat_chat_viet": med.get("ingredient_vi"),
                "hoat_chat_anh": med.get("ingredient_en"),
                "nhom_thuoc": med.get("category_vi"),
                "cong_dung": med.get("uses_vi") or [],
                "luu_y_quan_trong": med.get("important_notes_vi") or [],
                "lieu_dung_tu_don": {
                    "lieu": med.get("dose"),
                    "lich": med.get("schedule"),
                    "thoi_gian": med.get("duration"),
                },
                "muc_do_rui_ro": med.get("risk_level", "low"),
                "canh_bao_an_toan": med.get("safety_flags") or [],
                "da_tim_thay_trong_co_so_du_lieu": med.get("found", False),
            }
            # Remove None / empty values to keep context compact
            entry = {k: v for k, v in entry.items() if v not in (None, [], {})}
            entries.append(entry)

        return json.dumps(entries, ensure_ascii=False, indent=2)

    def _llm_fallback(fallback_answer: str = "", fallback_related: list | None = None) -> dict:
        """
        Call LLM agent with enriched internal drug data as context.
        If LLM is unavailable or fails, return fallback_answer instead of crashing.
        """
        from ..agent import answer_medication_question
        from ..services.prescription_store import get_prescription
        try:
            prescription = get_prescription(state.get("prescription_id", "")) or {}
            drug_context = _build_drug_context(state.get("mentioned_drug"), all_medications)
            result = answer_medication_question(
                prescription=prescription,
                message=state.get("question", ""),
                history=state.get("history", []),
                drug_context=drug_context,
            )
            return {
                **state,
                "answer": result.get("answer", ""),
                "quick_replies": result.get("quickReplies", MEDICATION_QUICK_REPLIES),
                "risk_level": "low",
                "related_medications": fallback_related or [],
            }
        except Exception:
            # LLM unavailable — return whatever partial answer we already have
            answer = fallback_answer or (
                "Xin lỗi, mình chưa đủ dữ liệu để trả lời câu hỏi này. "
                "Vui lòng hỏi trực tiếp dược sĩ hoặc bác sĩ kê đơn."
            )
            return {
                **state,
                "answer": answer,
                "quick_replies": MEDICATION_QUICK_REPLIES,
                "risk_level": "low",
                "related_medications": fallback_related or [],
            }

    if intent == "side_effects":
        answer, related, needs_llm = _build_side_effects_answer(medications)
        if needs_llm:
            # Drug not in local DB at all → LLM, with structured partial as fallback
            return _llm_fallback(fallback_answer=answer, fallback_related=related)
        risk_level = "medium"
    elif intent == "uses":
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
            "Bạn không nên tự ý tăng/giảm liều, ngưng hoặc thay thuốc. "
            "Nếu có tác dụng phụ hoặc muốn đổi thuốc, hãy hỏi bác sĩ/dược sĩ."
        )
        related = [m.get("raw_name") or m.get("name", "") for m in medications]
        risk_level = "high"
    elif intent == "interaction":
        answer, related = _build_interaction_answer(medications)
        risk_level = "medium"
    elif intent == "llm_fallback":
        return _llm_fallback()
    else:
        answer, related = _build_general_answer(medications)
        risk_level = "low"

    return {
        **state,
        "answer": answer,
        "quick_replies": MEDICATION_QUICK_REPLIES,
        "risk_level": risk_level,
        "related_medications": related,
    }
