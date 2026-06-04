"""LLM chat agent for medication Q&A.

This module handles LLM-based chat responses as a fallback
when rule-based intent detection cannot handle the question.
All safety rules are centralized in safety_service.py.
"""
import json
import os

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
from .services.safety_service import is_dangerous_request


def build_prompt(
    prescription: dict,
    message: str,
    history: list[dict] | None = None,
) -> list[dict]:
    """Build messages for LLM chat completion."""
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
    """
    Answer medication question via LLM.

    Falls back to dangerous request response if the question
    is flagged by safety_service.is_dangerous_request().
    """
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
