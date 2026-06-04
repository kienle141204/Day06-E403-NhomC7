"""LangGraph: Prescription Confirm — enrich medications after user confirmation.

Flow:
  check_confidence → lookup_local_db
    → (all found locally?) check_interactions
    → (some missing?)    map_vn_to_english → fetch_dailymed → check_interactions
    → build_enriched_prescription → END
"""
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..nodes.check_confidence import check_confidence
from ..nodes.lookup_local_db import lookup_local_db
from ..nodes.map_vn_to_english import map_vn_to_english
from ..nodes.fetch_dailymed import fetch_dailymed
from ..nodes.check_interactions import check_interactions
from ..nodes.build_enriched_prescription import build_enriched_prescription


class DrugLookupResult(TypedDict, total=False):
    raw_name: str
    found_locally: bool
    local_data: dict[str, Any]
    english_name: str | None
    dailymed_data: dict[str, Any] | None
    risk_level: str
    safety_flags: list[str]
    needs_specialist: bool


class ConfirmState(TypedDict, total=False):
    prescription_id: str
    raw_medications: list[dict[str, Any]]
    lookup_results: list[DrugLookupResult]
    has_high_risk: bool
    interaction_warnings: list[str]
    enriched_medications: list[dict[str, Any]]
    errors: list[str]


def _route_after_db_lookup(state: ConfirmState) -> str:
    """Skip external lookup if every drug was found locally."""
    results = state.get("lookup_results", [])
    if any(not r.get("found_locally") for r in results):
        return "map_vn_to_english"
    return "check_interactions"


def build_confirm_graph():
    graph = StateGraph(ConfirmState)

    graph.add_node("check_confidence", check_confidence)
    graph.add_node("lookup_local_db", lookup_local_db)
    graph.add_node("map_vn_to_english", map_vn_to_english)
    graph.add_node("fetch_dailymed", fetch_dailymed)
    graph.add_node("check_interactions", check_interactions)
    graph.add_node("build_enriched_prescription", build_enriched_prescription)

    graph.add_edge(START, "check_confidence")
    graph.add_edge("check_confidence", "lookup_local_db")
    graph.add_conditional_edges(
        "lookup_local_db",
        _route_after_db_lookup,
        {
            "map_vn_to_english": "map_vn_to_english",
            "check_interactions": "check_interactions",
        },
    )
    graph.add_edge("map_vn_to_english", "fetch_dailymed")
    graph.add_edge("fetch_dailymed", "check_interactions")
    graph.add_edge("check_interactions", "build_enriched_prescription")
    graph.add_edge("build_enriched_prescription", END)

    return graph.compile()


confirm_graph = build_confirm_graph()
