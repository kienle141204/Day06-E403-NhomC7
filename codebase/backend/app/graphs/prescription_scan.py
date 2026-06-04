import base64
import os
from datetime import date
from typing import Any, TypedDict
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from langgraph.graph import END, START, StateGraph

from ..schemas import Medication, Prescription, PrescriptionWarning, VisionPrescriptionResult
from ..vision import extract_prescription_from_image


SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
DEFAULT_MAX_UPLOAD_BYTES = 8 * 1024 * 1024


class ScanState(TypedDict, total=False):
    file_name: str
    mime_type: str
    image_bytes: bytes
    image_base64: str
    vision_result: VisionPrescriptionResult
    prescription: dict[str, Any]
    errors: list[str]


def _max_upload_bytes() -> int:
    value = os.getenv("MAX_SCAN_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES))
    try:
        return int(value)
    except ValueError:
        return DEFAULT_MAX_UPLOAD_BYTES


async def validate_upload(state: ScanState) -> ScanState:
    mime_type = state.get("mime_type") or ""
    image_bytes = state.get("image_bytes") or b""

    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(status_code=422, detail="Only JPEG, PNG, WEBP, HEIC, and HEIF prescription images are supported.")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(image_bytes) > _max_upload_bytes():
        raise HTTPException(status_code=413, detail="Uploaded image is too large.")

    return {
        **state,
        "image_base64": base64.b64encode(image_bytes).decode("ascii"),
    }


async def extract_with_vlm(state: ScanState) -> ScanState:
    result = await extract_prescription_from_image(
        image_base64=state["image_base64"],
        mime_type=state["mime_type"],
    )
    if not result.is_valid_prescription:
        detail = result.reason or "The image does not look like a readable prescription."
        raise HTTPException(status_code=422, detail=detail)

    if not result.medications:
        raise HTTPException(status_code=422, detail="No medication names were found. Please upload a clearer prescription image.")

    return {**state, "vision_result": result}


async def normalize_prescription(state: ScanState) -> ScanState:
    result = state["vision_result"]
    medications = [
        Medication(
            id=f"med-{index + 1}",
            name=item.name,
            strength=item.strength,
            dose=item.dose,
            schedule=item.schedule,
            duration=item.duration,
            risk="normal",
            confidence=item.confidence,
            notes=item.notes or "Extracted from prescription image. Please confirm before use.",
        )
        for index, item in enumerate(result.medications)
        if item.name.strip()
    ]

    if not medications:
        raise HTTPException(status_code=422, detail="No readable medication names were found. Please upload a clearer prescription image.")

    warnings = [
        PrescriptionWarning(
            id=f"warn-{index + 1}",
            level="medium",
            title="Please verify extracted prescription text",
            detail=warning,
        )
        for index, warning in enumerate(result.warnings)
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


def build_scan_graph():
    graph = StateGraph(ScanState)
    graph.add_node("validate_upload", validate_upload)
    graph.add_node("extract_with_vlm", extract_with_vlm)
    graph.add_node("normalize_prescription", normalize_prescription)

    graph.add_edge(START, "validate_upload")
    graph.add_edge("validate_upload", "extract_with_vlm")
    graph.add_edge("extract_with_vlm", "normalize_prescription")
    graph.add_edge("normalize_prescription", END)
    return graph.compile()


scan_graph = build_scan_graph()


async def scan_prescription_upload(file: UploadFile) -> dict[str, Any]:
    content = await file.read()
    state = await scan_graph.ainvoke(
        {
            "file_name": file.filename or "upload",
            "mime_type": file.content_type or "",
            "image_bytes": content,
            "errors": [],
        }
    )
    return state["prescription"]
