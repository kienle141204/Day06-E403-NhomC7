"""Chat node: append the current Q&A turn to the rolling session history."""
from app.services.prescription_store import get_prescription

_MAX_HISTORY = 12


async def append_history(state: dict) -> dict:
    """Append user question and assistant answer to history (max 12 messages)."""
    history = list(state.get("history") or [])
    question = state.get("question") or ""
    answer = state.get("answer") or ""

    history.extend([
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ])
    history = history[-_MAX_HISTORY:]

    prescription_id = state.get("prescription_id")
    if prescription_id:
        prescription = get_prescription(prescription_id)
        if prescription is not None:
            prescription["chat_history"] = history

    return {**state, "history": history}
