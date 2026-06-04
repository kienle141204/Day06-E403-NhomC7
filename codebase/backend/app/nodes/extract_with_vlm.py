"""Scan node: extract medication data from image via vision model."""
from fastapi import HTTPException

from ..vision import extract_prescription_from_image


async def extract_with_vlm(state: dict) -> dict:
    """Call OpenAI Vision model to extract prescription data from image."""
    result = await extract_prescription_from_image(
        image_base64=state["image_base64"],
        mime_type=state["mime_type"],
    )

    if not result.is_valid_prescription:
        raise HTTPException(
            status_code=422,
            detail=result.reason or "The image does not look like a readable prescription.",
        )
    if not result.medications:
        raise HTTPException(
            status_code=422,
            detail="No medication names were found. Please upload a clearer prescription image.",
        )

    return {**state, "vision_result": result}
