"""Confirm node: classify risk and check drug interactions."""
from ..services.safety_service import classify_risk, SAFETY_NOTICE


async def check_interactions(state: dict) -> dict:
    """
    Run safety_service.classify_risk on each resolved drug.

    Populates per-drug risk_level and safety_flags.
    Sets has_high_risk=True and appends to interaction_warnings if any drug is high risk.
    When dailymed_data is present, its warnings field supplements the classification.
    """
    results = list(state.get("lookup_results", []))
    interaction_warnings: list[str] = list(state.get("interaction_warnings", []))
    has_high_risk = False

    for r in results:
        # Build a resolved-med dict that classify_risk understands
        source = r.get("local_data") or {}
        if r.get("dailymed_data"):
            dm = r["dailymed_data"]
            source = {**source, "important_notes_vi": [dm.get("warnings", "")]}

        risk_level, safety_flags = classify_risk({
            **source,
            "needs_review": not r.get("found_locally"),
            "confidence": source.get("confidence", 0.5 if not r.get("found_locally") else 1.0),
        })

        r["risk_level"] = risk_level
        r["safety_flags"] = safety_flags

        if risk_level == "high":
            has_high_risk = True
            r["needs_specialist"] = True
            interaction_warnings.append(
                f"⚠️ {r['raw_name']}: {', '.join(safety_flags) or 'Thuốc nguy cơ cao'}"
            )

    return {
        **state,
        "lookup_results": results,
        "has_high_risk": has_high_risk,
        "interaction_warnings": interaction_warnings,
    }
