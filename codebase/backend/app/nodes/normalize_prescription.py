"""Scan node: normalize vision result into frontend Prescription shape."""
from datetime import date
from uuid import uuid4

from fastapi import HTTPException

from ..schemas import Medication, Prescription, PrescriptionWarning


async def normalize_prescription(state: dict) -> dict:
    """Convert VisionPrescriptionResult into the Prescription dict the frontend expects."""
    result = state["vision_result"]

    medications = [
        Medication(
            id=f"med-{i + 1}",
            name=item.name,
            strength=item.strength,
            dose=item.dose,
            schedule=item.schedule,
            duration=item.duration,
            risk="normal",
            confidence=item.confidence,
            notes=item.notes or "Extracted from prescription image. Please confirm before use.",
        )
        for i, item in enumerate(result.medications)
        if item.name.strip()
    ]

    if not medications:
        raise HTTPException(
            status_code=422,
            detail="No readable medication names were found. Please upload a clearer prescription image.",
        )

    warnings = [
        PrescriptionWarning(
            id=f"warn-{i + 1}",
            level="medium",
            title="Please verify extracted prescription text",
            detail=warning,
        )
        for i, warning in enumerate(result.warnings)
        if warning.strip()
    ]

    prescription = Prescription(
        prescriptionId=f"rx-{uuid4().hex[:10]}",
        confidence=result.confidence,
        doctorName=result.doctor_name or "Unknown doctor",
        clinic=result.clinic or "Unknown clinic",
        issuedAt=result.issued_at or date.today().isoformat(),
        status="pending",
        medications=medications,
        warnings=warnings,
    )

    return {**state, "prescription": prescription.model_dump()}
