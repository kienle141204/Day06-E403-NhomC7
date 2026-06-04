"""Chat node: append the current Q&A turn to the rolling session history."""
from ..services.prescription_store import get_prescription

_MAX_HISTORY = 12


async def append_history(state: dict) -> dict:
    """Append user question and assistant answer to history (max 12 messages)."""
    history = list(state.get("history", []))
    question = state.get("question", "")
    answer = state.get("answer", "")

    history.extend([
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ])
    history = history[-_MAX_HISTORY:]

    return {**state, "history": history}
