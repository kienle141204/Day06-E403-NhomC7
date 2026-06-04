"""Chat node: classify the user's question into a known intent."""
import re

INTENTS: dict[str, list[str]] = {
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


async def detect_intent(state: dict) -> dict:
    """Classify the question into one of the known intents, or 'llm_fallback'."""
    normalized = _normalize(state.get("question", ""))
    intent = "llm_fallback"
    for name, keywords in INTENTS.items():
        if any(kw in normalized for kw in keywords):
            intent = name
            break
    return {**state, "intent": intent}
