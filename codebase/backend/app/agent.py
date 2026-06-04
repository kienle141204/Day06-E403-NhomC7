import json
import os
import re
import unicodedata

from fastapi import HTTPException
from openai import OpenAI

from .prompts import (
    DANGEROUS_REQUEST_ANSWER,
    EMPTY_ANSWER,
    MEDICATION_AGENT_PROMPT,
    MEDICATION_QUICK_REPLIES,
    PRESCRIPTION_CONTEXT_TEMPLATE,
    USER_MESSAGE_TEMPLATE,
)


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


def normalize_text(value: str) -> str:
    value = value.replace("đ", "d").replace("Đ", "d")
    normalized = unicodedata.normalize("NFD", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").lower()


def is_dangerous_request(message: str) -> bool:
    normalized = normalize_text(message)
    return any(re.search(pattern, normalized) for pattern in DANGEROUS_REQUEST_PATTERNS)


def build_prompt(
    prescription: dict,
    message: str,
    history: list[dict] | None = None,
) -> list[dict]:
    prescription_json = json.dumps(prescription, ensure_ascii=False, indent=2)
    messages = [
        {"role": "developer", "content": MEDICATION_AGENT_PROMPT},
        {
            "role": "user",
            "content": PRESCRIPTION_CONTEXT_TEMPLATE.format(prescription_json=prescription_json),
        },
    ]
    messages.extend(history or [])
    messages.append({"role": "user", "content": USER_MESSAGE_TEMPLATE.format(message=message)})
    return messages


def answer_medication_question(
    prescription: dict,
    message: str,
    history: list[dict] | None = None,
) -> dict:
    if is_dangerous_request(message):
        return {
            "answer": DANGEROUS_REQUEST_ANSWER,
            "quickReplies": MEDICATION_QUICK_REPLIES,
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured for medication chat.",
        )

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=model,
            input=build_prompt(prescription, message, history),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI chat failed: {exc}") from exc

    answer = getattr(response, "output_text", "") or EMPTY_ANSWER
    return {
        "answer": answer.strip(),
        "quickReplies": MEDICATION_QUICK_REPLIES,
    }
