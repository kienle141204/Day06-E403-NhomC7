"""Shared utilities for text processing."""
import re
import unicodedata

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


def to_ascii(text: str) -> str:
    """Convert Vietnamese text to ASCII by replacing accented characters."""
    return "".join(VIETNAMESE_MAP.get(c, c) for c in text)


def normalize_for_match(text: str) -> str:
    """Normalize text for matching (to ASCII, lowercase)."""
    if not text:
        return ""
    return to_ascii(text).lower()


def normalize_question(text: str) -> str:
    """Normalize Vietnamese text: to ASCII, lowercase, collapse spaces."""
    if not text:
        return ""
    text = to_ascii(text)
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def normalize_text(value: str) -> str:
    """Normalize text: lowercase, remove accents, collapse spaces."""
    value = value.replace("đ", "d").replace("Đ", "d")
    normalized = unicodedata.normalize("NFD", value)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn").lower()
