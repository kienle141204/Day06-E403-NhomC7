"""Confirm node: resolve each medication against local drug database via fuzzy matching."""
from ..services.drug_data_service import get_drug_data_service


async def lookup_local_db(state: dict) -> dict:
    """
    For each medication, attempt a fuzzy match against the local datathuoc_enriched.json.

    Populates each DrugLookupResult with:
      - found_locally: bool
      - local_data: resolved medication dict (or {}) from drug_data_service
    """
    drug_service = get_drug_data_service()
    raw_meds = state.get("raw_medications", [])
    lookup_results = []

    for med in raw_meds:
        raw_name = med.get("name") or med.get("raw_name") or ""
        resolved = drug_service.resolve_to_medication_dict(
            raw_name=raw_name,
            dosage=med.get("dose") or med.get("dosage"),
            frequency=med.get("schedule") or med.get("frequency"),
            duration=med.get("duration"),
        )
        lookup_results.append({
            "raw_name": raw_name,
            "found_locally": resolved.get("found", False),
            "local_data": resolved,
            "english_name": None,
            "dailymed_data": None,
            "risk_level": "low",
            "safety_flags": [],
            "needs_specialist": False,
        })

    return {**state, "lookup_results": lookup_results}
