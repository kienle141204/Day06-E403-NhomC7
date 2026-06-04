"""Chat node: detect and short-circuit dangerous medical requests."""
from ..agent import is_dangerous_request
from ..prompts import DANGEROUS_REQUEST_ANSWER, MEDICATION_QUICK_REPLIES


async def guard_dangerous_request(state: dict) -> dict:
    """
    Check if the user's question crosses a safety boundary.

    Dangerous = requests to diagnose, change dose, stop/swap medications.
    If dangerous, pre-fills answer so the graph can skip to append_history.
    """
    question = state.get("question", "")
    dangerous = is_dangerous_request(question)

    if dangerous:
        return {
            **state,
            "is_dangerous": True,
            "answer": DANGEROUS_REQUEST_ANSWER,
            "quick_replies": MEDICATION_QUICK_REPLIES,
            "risk_level": "high",
        }

    return {**state, "is_dangerous": False}
