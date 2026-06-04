"""LangGraph: generate medication reminders from a confirmed prescription."""
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..nodes.create_reminders import create_reminders


class RemindersState(TypedDict, total=False):
    prescription_id: str
    prescription: dict[str, Any]
    leadMinutes: int
    reminders: list[dict[str, str]]
    errors: list[str]


def build_reminders_graph():
    graph = StateGraph(RemindersState)
    graph.add_node("create_reminders", create_reminders)
    graph.add_edge(START, "create_reminders")
    graph.add_edge("create_reminders", END)
    return graph.compile()


reminders_graph = build_reminders_graph()
