"""Scan node: validate uploaded image before OCR."""
import base64
import os

from fastapi import HTTPException

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
_DEFAULT_MAX_BYTES = 8 * 1024 * 1024


def _max_upload_bytes() -> int:
    try:
        return int(os.getenv("MAX_SCAN_UPLOAD_BYTES", str(_DEFAULT_MAX_BYTES)))
    except ValueError:
        return _DEFAULT_MAX_BYTES


async def validate_upload(state: dict) -> dict:
    """Validate MIME type and file size; encode image to base64."""
    mime_type = state.get("mime_type") or ""
    image_bytes = state.get("image_bytes") or b""

    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Only JPEG, PNG, WEBP, HEIC, and HEIF prescription images are supported.",
        )
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(image_bytes) > _max_upload_bytes():
        raise HTTPException(status_code=413, detail="Uploaded image is too large.")

    return {**state, "image_base64": base64.b64encode(image_bytes).decode("ascii")}
