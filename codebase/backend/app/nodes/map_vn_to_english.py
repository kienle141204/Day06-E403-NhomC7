"""Confirm node (STUB): map Vietnamese drug trade names to English/INN generic names.

TODO: Implement one of the following approaches:
  1. Static JSON dictionary — add a file `data/vn_to_english_map.json` mapping
     common Vietnamese trade names to INN/generic names, then load and lookup here.
  2. Embedding search — embed `ingredient_en` values from datathuoc_enriched.json
     and do a cosine-similarity search against the normalized Vietnamese name.
  3. LLM prompt — call the OpenAI API with:
       "Given the Vietnamese drug trade name '{name}', return only the INN generic
        name in English, or null if unknown."
     Use a cheap model (gpt-4o-mini) with temperature=0 for determinism.

Input state keys read:  lookup_results[*].found_locally, lookup_results[*].raw_name
Output state keys set:  lookup_results[*].english_name (str | None)
"""


async def map_vn_to_english(state: dict) -> dict:
    """Map unresolved Vietnamese drug names to English INN names. Currently a stub."""
    results = list(state.get("lookup_results", []))
    for r in results:
        if not r.get("found_locally"):
            # STUB — always returns None until real mapping is implemented
            r["english_name"] = None
    return {**state, "lookup_results": results}
