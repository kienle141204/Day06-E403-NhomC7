import json
import os
import re

from fastapi import HTTPException
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from .schemas import VisionPrescriptionResult


VISION_PROMPT = """
You are a medical prescription OCR assistant.

Read the uploaded prescription image and return JSON only. Do not add markdown.

Rules:
- If the image is not a prescription or is too blurry to read medications, set is_valid_prescription to false and explain in reason.
- Extract only text visible in the image. Do not invent medicines.
- Use null-safe empty strings when fields are missing.
- Confidence values must be numbers from 0 to 1.
- Keep medication names as written if unsure.

Return this JSON shape:
{
  "is_valid_prescription": true,
  "confidence": 0.0,
  "doctor_name": "",
  "clinic": "",
  "issued_at": "YYYY-MM-DD or original visible date",
  "medications": [
    {
      "name": "",
      "strength": "",
      "dose": "",
      "schedule": "",
      "duration": "",
      "confidence": 0.0,
      "notes": ""
    }
  ],
  "warnings": [],
  "reason": ""
}
""".strip()


def _message_content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content)


def _extract_json(value: str) -> dict:
    text = value.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Vision model returned invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="Vision model returned a non-object JSON payload.")
    return parsed


async def extract_prescription_from_image(image_base64: str, mime_type: str) -> VisionPrescriptionResult:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured for prescription scan.")

    model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model, api_key=api_key, temperature=0)
    data_url = f"data:{mime_type};base64,{image_base64}"

    try:
        response = await llm.ainvoke(
            [
                HumanMessage(
                    content=[
                        {"type": "text", "text": VISION_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]
                )
            ]
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI vision scan failed: {exc}") from exc

    parsed = _extract_json(_message_content_to_text(response.content))
    try:
        return VisionPrescriptionResult.model_validate(parsed)
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail=f"Vision model JSON did not match scan schema: {exc}") from exc
