"""Confirm node: annotate each medication with needs_review flag."""
from ..config import CONFIDENCE_THRESHOLD


async def check_confidence(state: dict) -> dict:
    """Flag medications whose OCR confidence is below the threshold for user review."""
    medications = state.get("raw_medications", [])
    annotated = []
    for med in medications:
        m = dict(med)
        m["needs_review"] = m.get("confidence", 1.0) < CONFIDENCE_THRESHOLD
        annotated.append(m)
    return {**state, "raw_medications": annotated}
