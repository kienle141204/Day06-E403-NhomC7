"""Analysis service for prescription analysis."""
from typing import List, Dict, Any

from app.services.drug_data_service import get_drug_data_service
from app.services.safety_service import classify_risk, get_safety_notice
from app.services.prescription_store import get_prescription


def analyze_prescription(prescription_id: str) -> Dict[str, Any]:
    """
    Analyze a prescription and return analysis result.
    
    Uses deterministic summary generation (no LLM).
    """
    prescription = get_prescription(prescription_id)
    if not prescription:
        raise ValueError(f"Prescription {prescription_id} not found")
    
    confirmed_meds = prescription.get("confirmed_medications") or prescription.get("medications", [])
    drug_service = get_drug_data_service()
    
    resolved_medications: List[Dict] = []
    high_risk_warnings: List[str] = []
    need_review_count = 0
    high_risk_count = 0
    
    for med in confirmed_meds:
        # Resolve drug from local database
        resolved = drug_service.resolve_to_medication_dict(
            raw_name=med.get("raw_name") or med.get("name", ""),
            dosage=med.get("dosage"),
            frequency=med.get("frequency"),
            duration=med.get("duration")
        )
        
        # Classify risk
        risk_level, safety_flags = classify_risk(resolved)
        resolved["risk_level"] = risk_level
        resolved["safety_flags"] = safety_flags
        
        resolved_medications.append(resolved)
        
        # Count for summary
        if risk_level == "high":
            high_risk_count += 1
            high_risk_warnings.append(
                f"⚠️ {resolved.get('raw_name', 'Unknown')}: {resolved.get('category_vi', 'Unknown category')}"
            )
        
        if resolved.get("needs_review", False):
            need_review_count += 1
            if resolved.get("raw_name") not in [w.split(" ")[1] for w in high_risk_warnings]:
                high_risk_warnings.append(
                    f"🔍 {resolved.get('raw_name', 'Unknown')}: Cần xác minh thông tin"
                )
    
    # Generate deterministic summary
    total_meds = len(resolved_medications)
    summary_parts = [f"Đơn thuốc có {total_meds} thuốc."]
    
    if need_review_count > 0:
        summary_parts.append(f"Có {need_review_count} thuốc cần kiểm tra lại.")
    
    if high_risk_count > 0:
        summary_parts.append(f"Có {high_risk_count} thuốc nguy cơ cao cần hỏi bác sĩ/dược sĩ.")
    
    summary = " ".join(summary_parts)
    
    return {
        "prescription_id": prescription_id,
        "summary": summary,
        "medications": resolved_medications,
        "high_risk_warnings": high_risk_warnings,
        "safety_notice": get_safety_notice()
    }
