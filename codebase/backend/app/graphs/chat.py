"""LangGraph: Chat — detect intent → build answer → append history.

Flow:
  guard_dangerous_request
    → (dangerous)    build_answer (pre-filled refuse) → append_history → END
    → (safe)         detect_intent → build_answer → append_history → END
"""
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..nodes.guard_dangerous_request import guard_dangerous_request
from ..nodes.detect_intent import detect_intent
from ..nodes.build_answer import build_answer
from ..nodes.append_history import append_history


class ChatState(TypedDict, total=False):
    prescription_id: str
    question: str
    session_id: str
    history: list[dict[str, str]]
    medications: list[dict[str, Any]]
    intent: str
    mentioned_drug: dict[str, Any] | None   # set by detect_intent; None = general question
    is_dangerous: bool
    answer: str
    quick_replies: list[str]
    risk_level: str
    related_medications: list[str]
    errors: list[str]


def _route_after_guard(state: ChatState) -> str:
    return "build_answer" if state.get("is_dangerous") else "detect_intent"


def build_chat_graph():
    graph = StateGraph(ChatState)

    graph.add_node("guard_dangerous_request", guard_dangerous_request)
    graph.add_node("detect_intent", detect_intent)
    graph.add_node("build_answer", build_answer)
    graph.add_node("append_history", append_history)

    graph.add_edge(START, "guard_dangerous_request")
    graph.add_conditional_edges(
        "guard_dangerous_request",
        _route_after_guard,
        {
            "build_answer": "build_answer",
            "detect_intent": "detect_intent",
        },
    )
    graph.add_edge("detect_intent", "build_answer")
    graph.add_edge("build_answer", "append_history")
    graph.add_edge("append_history", END)

    return graph.compile()


chat_graph = build_chat_graph()
