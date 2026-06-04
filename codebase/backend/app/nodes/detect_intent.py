"""Chat node: classify the user's question into a known intent.

Also extracts `mentioned_drug` — the specific medication from the prescription
that the user is asking about (if any). build_answer uses this to filter responses.
"""
import re

INTENTS: dict[str, list[str]] = {
    # side_effects TRƯỚC uses để "tac dung phu" không bị "tac dung" của uses chặn trước
    "side_effects": [
        "tac dung phu", "phan ung phu", "side effect", "tac hai",
        "co hai gi", "anh huong gi", "anh huong khong", "gay ra gi",
        "nguy hiem khong", "can than gi",
    ],
    "uses": [
        "cong dung", "dung de lam gi", "co tac dung gi", "co tac gi",
        "thuoc gi", "la thuoc gi", "dieu tri gi", "tri gi", "chua gi",
    ],
    "drowsiness": ["buon ngu", "lai xe", "chong mat", "choang vang", "choang", "met moi"],
    "antibiotic": ["khang sinh", "antibiotic"],
    "schedule": [
        "lich uong", "ngay may lan", "may lan mot ngay", "bao nhieu lan",
        "truoc an", "sau an", "gio uong", "luc nao uong", "uong khi nao",
        "uong the nao",
    ],
    "dose_change": [
        "tang lieu", "giam lieu", "gap doi", "ngung thuoc", "bo thuoc",
        "doi thuoc", "thay thuoc", "them thuoc", "bot thuoc", "them lieu", "bot lieu",
    ],
    "interaction": ["tuong tac", "uong chung", "ruou", "bia"],
}

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


def _normalize(text: str) -> str:
    text = _to_ascii(text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _matches_keyword(keyword: str, padded_question: str) -> bool:
    """
    Whole-word / whole-phrase match.

    Padding the question with spaces means ' keyword ' never matches
    inside a longer word. E.g. 'nga' won't match inside 'ngay'.
    """
    return f" {keyword} " in padded_question


def _extract_mentioned_drug(padded_question: str, medications: list) -> dict | None:
    """
    Check if the question mentions a specific drug from the prescription.

    Uses whole-word matching on each token of the drug name (min 4 chars).
    Returns the medication dict if found, None for general questions.
    """
    for med in medications:
        full_name = med.get("raw_name") or med.get("name") or ""
        ingredient = med.get("ingredient_vi") or med.get("ingredient_en") or ""
        candidates = [full_name, ingredient]

        for candidate in candidates:
            for token in candidate.split():
                token_norm = _normalize(token)
                if len(token_norm) >= 4 and f" {token_norm} " in padded_question:
                    return med

    return None


async def detect_intent(state: dict) -> dict:
    """
    Classify the question into one of the known intents, or 'llm_fallback'.

    Uses whole-word matching so short tokens like 'nga' don't fire inside
    unrelated words like 'ngay' (ngày).

    Also sets 'mentioned_drug' to the specific medication dict if the user
    named a drug from the prescription, or None for general questions.
    """
    question_norm = _normalize(state.get("question", ""))
    # Pad with spaces so boundary checks work at start/end of string too
    padded = f" {question_norm} "
    medications = state.get("medications", [])

    intent = "llm_fallback"
    for name, keywords in INTENTS.items():
        if any(_matches_keyword(kw, padded) for kw in keywords):
            intent = name
            break

    mentioned_drug = _extract_mentioned_drug(padded, medications)

    return {**state, "intent": intent, "mentioned_drug": mentioned_drug}
