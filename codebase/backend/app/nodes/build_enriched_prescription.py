"""Confirm node: assemble enriched medication list for the frontend."""


def _merge_medication(raw_med: dict, lookup: dict) -> dict:
    """
    Merge original OCR/user-edited medication dict with lookup results.

    Priority: user-edited fields > local_data > dailymed_data
    """
    local = lookup.get("local_data") or {}
    dailymed = lookup.get("dailymed_data") or {}

    # Risk mapping: internal risk_level → frontend risk field
    risk_map = {"high": "high", "medium": "normal", "low": "normal"}

    enriched = {
        # Preserve all original OCR/user fields
        **raw_med,
        # Overlay resolved data (non-destructive: only fill if original is empty)
        "category_vi": local.get("category_vi") or raw_med.get("category_vi"),
        "ingredient_vi": local.get("ingredient_vi") or raw_med.get("ingredient_vi"),
        "ingredient_en": local.get("ingredient_en") or lookup.get("english_name"),
        "uses_vi": local.get("uses_vi") or (
            [dailymed.get("indications")] if dailymed.get("indications") else []
        ),
        "important_notes_vi": local.get("important_notes_vi") or (
            [dailymed.get("warnings")] if dailymed.get("warnings") else []
        ),
        "dosage_info": local.get("dosage") or dailymed.get("dosage"),
        # Risk for frontend display
        "risk": risk_map.get(lookup.get("risk_level", "low"), "normal"),
        # Internal fields used by chat service
        "risk_level": lookup.get("risk_level", "low"),
        "safety_flags": lookup.get("safety_flags", []),
        "found": lookup.get("found_locally", False),
        "needs_review": not lookup.get("found_locally", False),
        "raw_name": lookup.get("raw_name") or raw_med.get("name", ""),
        "source": local.get("source"),
    }
    return enriched


async def build_enriched_prescription(state: dict) -> dict:
    """Merge lookup results back into medication dicts the frontend expects."""
    raw_meds = state.get("raw_medications", [])
    lookup_results = state.get("lookup_results", [])

    # Pair by index — both lists were built from the same raw_medications
    enriched_medications = [
        _merge_medication(raw, lookup)
        for raw, lookup in zip(raw_meds, lookup_results)
    ]

    return {**state, "enriched_medications": enriched_medications}
