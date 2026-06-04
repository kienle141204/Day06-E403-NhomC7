"""Chat node: build the answer based on detected intent."""
from app.prompts import MEDICATION_QUICK_REPLIES
from app.services.text_utils import normalize_for_match

JOIN = "".join

def build_uses(medications):
    related = []
    lines = ["Cong dung cua cac thuoc trong don:"]
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        uses = med.get("uses_vi") or []
        related.append(name)
        if not med.get("found"):
            lines.append("- " + name + ": Chua tim thay thong tin, can hoi duoc si/bac si.")
        elif uses and any(u for u in uses if u):
            uses_text = "; ".join(u for u in uses if u)
            lines.append("- " + name + ": " + uses_text)
        else:
            lines.append("- " + name + ": Chua co du du lieu cong dung, can hoi duoc si/bac si.")
    return JOIN(lines), related

def build_drowsiness(medications):
    related = []
    lines = ["Cac thuoc co the gay buon ngu hoac chong mat:"]
    found_any = False
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        category = normalize_for_match(med.get("category_vi") or "")
        notes_list = med.get("important_notes_vi") or []
        notes_text = normalize_for_match(" ".join(notes_list))
        drowsy_keywords = ["khang histamin", "chong di ung", "buon ngu", "chong mat", "lai xe", "nga"]
        is_drowsy = False
        for kw in drowsy_keywords:
            if kw in category or kw in notes_text:
                is_drowsy = True
                break
        if is_drowsy:
            found_any = True
            related.append(name)
            valid_notes = [n for n in notes_list if n]
            if valid_notes:
                note_text = "; ".join(valid_notes)
                lines.append("- " + name + ": " + note_text)
            else:
                lines.append("- " + name + ": Thuoc co the gay buon ngu nhe.")
    if not found_any:
        lines.append("Trong du lieu hien tai chua thay thuoc nao ghi chu ro ve buon ngu.")
        lines.append("Neu ban thay buon ngu/chong mat, nen tran lai xe va hoi duoc si/bac si.")
    return JOIN(lines), related

def build_antibiotic(medications):
    related = []
    lines = ["Cac thuoc khang sinh trong don:"]
    found_any = False
    antibiotic_keywords = ["khang sinh", "amoxicillin", "azithromycin", "ciprofloxacin", "metronidazole", "cephalosporin"]
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        category = normalize_for_match(med.get("category_vi") or "")
        ingredient = normalize_for_match(med.get("ingredient_vi") or "")
        is_antibiotic = False
        for kw in antibiotic_keywords:
            if kw in category or kw in ingredient:
                is_antibiotic = True
                break
        if is_antibiotic:
            found_any = True
            related.append(name)
            cat_orig = med.get("category_vi") or ""
            if cat_orig:
                lines.append("- " + name + " (" + cat_orig + ")")
            else:
                lines.append("- " + name)
    if not found_any:
        lines.append("Khong co thuoc khang sinh nao trong don nay.")
    else:
        lines.append("")
        lines.append("Luu y: Khong tu y ngung khang sinh giua chung khi chua hoi bac si.")
    return JOIN(lines), related

def build_schedule(medications):
    related = []
    lines = ["Lich uong thuoc theo don da xac nhan:"]
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        dosage = med.get("dosage") or med.get("dose") or "1 vien"
        frequency = med.get("frequency") or med.get("schedule") or ""
        duration = med.get("duration") or ""
        related.append(name)
        parts = [dosage]
        if frequency:
            parts.append(frequency)
        if duration:
            parts.append("trong " + duration)
        lines.append("- " + name + ": " + ", ".join(parts))
    if not related:
        lines.append("Khong co thong tin lich uong trong don.")
    return JOIN(lines), related

def build_interaction(medications):
    related = []
    lines = ["Ve tuong tac thuoc trong don:"]
    high_risk_names = []
    for m in medications:
        if m.get("risk_level") == "high":
            name = m.get("raw_name") or m.get("name", "Unknown")
            high_risk_names.append(name)
            related.append(name)
    if high_risk_names:
        lines.append("Cac thuoc can luu y: " + ", ".join(high_risk_names))
    else:
        lines.append("Chua phat hien thuoc nguy co cao trong don.")
    lines.append("")
    lines.append("Minh chua du du lieu khang dinh tuong tac thuoc day du. Hay hoi duoc si/bac si.")
    return JOIN(lines), related

def build_general(medications):
    related = []
    lines = ["Tom tat cac thuoc trong don da xac nhan:"]
    for med in medications:
        name = med.get("raw_name") or med.get("name", "Unknown")
        related.append(name)
        cat = med.get("category_vi") or ""
        if cat:
            lines.append("- " + name + " (" + cat + ")")
        else:
            lines.append("- " + name)
    lines.append("")
    lines.append("Ban co the hoi toi ve:")
    lines.append("- Cong dung")
    lines.append("- Khang sinh")
    lines.append("- Buon ngu")
    lines.append("- Lich uong")
    return JOIN(lines), related

async def build_answer(state):
    if state.get("is_dangerous"):
        return state

    intent = state.get("intent", "llm_fallback")
    medications = state.get("medications", [])

    if intent == "uses":
        answer, related = build_uses(medications)
        risk_level = "low"
    elif intent == "drowsiness":
        answer, related = build_drowsiness(medications)
        risk_level = "medium"
    elif intent == "antibiotic":
        answer, related = build_antibiotic(medications)
        risk_level = "medium"
    elif intent == "schedule":
        answer, related = build_schedule(medications)
        risk_level = "low"
    elif intent == "dose_change":
        answer = "Ban khong nen tu y tang/giam lieu, ngung hoac thay thuoc. Neu co tac dung phu hoac muon doi thuoc, hay hoi bac si/duoc si."
        related = []
        for m in medications:
            name = m.get("raw_name") or m.get("name", "")
            if name:
                related.append(name)
        risk_level = "high"
    elif intent == "interaction":
        answer, related = build_interaction(medications)
        risk_level = "medium"
    elif intent == "llm_fallback":
        from app.agent import answer_medication_question
        from app.services.prescription_store import get_prescription
        prescription = get_prescription(state.get("prescription_id") or "") or {}
        result = answer_medication_question(
            prescription=prescription,
            message=state.get("question") or "",
            history=state.get("history") or [],
        )
        return {
            **state,
            "answer": result.get("answer") or "",
            "quick_replies": result.get("quickReplies") or MEDICATION_QUICK_REPLIES,
            "risk_level": "low",
            "related_medications": [],
        }
    else:
        answer, related = build_general(medications)
        risk_level = "low"

    return {
        **state,
        "answer": answer,
        "quick_replies": MEDICATION_QUICK_REPLIES,
        "risk_level": risk_level,
        "related_medications": related,
    }
