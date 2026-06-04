"""Confirm node (STUB): fetch drug label data from the DailyMed API.

TODO: Implement using the DailyMed public API (no auth required):
  Base URL:  https://dailymed.nlm.nih.gov/dailymed/services/v2/
  Step 1 — search by drug name:
    GET /spls/search.json?drug_name=<english_name>&pagesize=1
    → parse response["data"][0]["setid"]
  Step 2 — fetch full label:
    GET /spls/<setid>.json
    → parse fields: indications_and_usage, dosage_and_administration,
                    warnings, adverse_reactions, drug_interactions
  Rate limit: ~240 requests/minute (free, no key needed).
  Recommended: cache results by english_name to avoid redundant calls.
  Set env var DAILYMED_TIMEOUT_SECONDS (default 5) for request timeout.

Input state keys read:  lookup_results[*].english_name (str | None)
Output state keys set:  lookup_results[*].dailymed_data (dict | None)
  dailymed_data shape: {
    "indications": str,
    "dosage": str,
    "warnings": str,
    "adverse_reactions": str,
  }
"""


async def fetch_dailymed(state: dict) -> dict:
    """Fetch DailyMed label data for drugs with a known English name. Currently a stub."""
    results = list(state.get("lookup_results", []))
    for r in results:
        if r.get("english_name"):
            # STUB — always returns None until HTTP integration is implemented
            r["dailymed_data"] = None
    return {**state, "lookup_results": results}
