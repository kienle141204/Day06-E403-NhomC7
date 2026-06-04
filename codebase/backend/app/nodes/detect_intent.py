"""Chat node: classify the user's question into a known intent."""
from app.services.text_utils import normalize_question

INTENTS = {
    "uses": ["cong dung", "dung de lam gi", "tac dung", "co tac dung gi", "chi co tac dung", "lam gi"],
    "drowsiness": ["buon ngu", "lai xe", "choang", "met", "drowsiness", "nga", "chong mat"],
    "antibiotic": ["khang sinh", "antibiotic"],
    "schedule": ["lich", "ngay may lan", "truoc an", "sau an", "gio uong", "luc nao uong"],
    "dose_change": [
        "tang lieu", "giam lieu", "gap doi", "ngung", "bo thuoc", "doi thuoc", "thay thuoc",
        "tang giam", "them thuoc", "bot thuoc", "them lieu", "bot lieu",
    ],
    "interaction": ["tuong tac", "uong chung", "ruou", "bia"],
}


async def detect_intent(state: dict) -> dict:
    """Classify the question into one of the known intents, or 'llm_fallback'."""
    normalized = normalize_question(state.get("question", ""))
    intent = "llm_fallback"
    for name, keywords in INTENTS.items():
        if any(kw in normalized for kw in keywords):
            intent = name
            break
    return {**state, "intent": intent}
