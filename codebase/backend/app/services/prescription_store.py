"""In-memory prescription store."""
from typing import Dict, Optional, Any

PRESCRIPTIONS: Dict[str, dict] = {}


def save_extracted(prescription_id: str, medications: list):
    """Save extracted medications."""
    PRESCRIPTIONS[prescription_id] = {
        "status": "extracted",
        "medications": medications,
        "confirmed_medications": None,
        "analysis": None
    }


def save_confirmed(prescription_id: str, medications: list):
    """Save user-confirmed medications."""
    if prescription_id in PRESCRIPTIONS:
        PRESCRIPTIONS[prescription_id]["status"] = "confirmed"
        PRESCRIPTIONS[prescription_id]["confirmed_medications"] = medications


def save_analysis(prescription_id: str, analysis: dict):
    """Save prescription analysis."""
    if prescription_id in PRESCRIPTIONS:
        PRESCRIPTIONS[prescription_id]["status"] = "analyzed"
        PRESCRIPTIONS[prescription_id]["analysis"] = analysis


def save_enriched(prescription_id: str, enriched_medications: list):
    """Save enriched medications produced by confirm_graph."""
    if prescription_id in PRESCRIPTIONS:
        PRESCRIPTIONS[prescription_id]["status"] = "confirmed"
        PRESCRIPTIONS[prescription_id]["confirmed_medications"] = enriched_medications
        PRESCRIPTIONS[prescription_id]["medications"] = enriched_medications


def get_prescription(prescription_id: str) -> Optional[dict]:
    """Get prescription by ID."""
    return PRESCRIPTIONS.get(prescription_id)
