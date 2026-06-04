"""FastAPI application — thin HTTP adapter. All business logic lives in LangGraph graphs."""
import os
import uuid
from copy import deepcopy
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.graphs import scan_prescription_upload, confirm_graph, chat_graph, reminders_graph
from app.services import (
    save_extracted,
    save_enriched,
    get_prescription,
)

app = FastAPI(
    title="MedChat API",
    description="Healthcare chatbot backend for prescription analysis",
    version="2.0.0",
)

_FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")
_ALLOW_ORIGINS = ["*"] if _FRONTEND_ORIGIN == "*" else [_FRONTEND_ORIGIN, "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory prescription + chat session stores
prescriptions: dict[str, dict] = {}
chat_sessions: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class MedicationPatch(BaseModel):
    name: str | None = None
    strength: str | None = None
    dose: str | None = None
    schedule: str | None = None
    duration: str | None = None


class ConfirmResponse(BaseModel):
    prescriptionId: str
    status: str
    medications: list


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    prescription_id: Optional[str] = Field(default=None, alias="prescriptionId")
    question: Optional[str] = Field(default=None, alias="message")


class ChatResponseFrontend(BaseModel):
    answer: str
    quickReplies: Optional[list] = None
    risk_level: Optional[str] = None


class ReminderItem(BaseModel):
    medicationId: str
    label: str
    time: str


class ReminderBulkRequest(BaseModel):
    prescriptionId: str
    leadMinutes: int = 60
    items: list[ReminderItem]


class AppointmentRequest(BaseModel):
    prescriptionId: str | None = None
    specialistId: str
    slot: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_prescription_or_404(prescription_id: str) -> dict:
    p = prescriptions.get(prescription_id)
    if not p:
        raise HTTPException(status_code=404, detail="Prescription not found.")
    return p


def _get_chat_session(session_id: str, prescription_id: str) -> dict:
    session = chat_sessions.setdefault(
        session_id, {"prescriptionId": prescription_id, "history": []}
    )
    if session["prescriptionId"] != prescription_id:
        raise HTTPException(
            status_code=409,
            detail="This chat session is already locked to another prescription.",
        )
    return session


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "MedChat API"}


@app.post("/prescriptions/scan")
async def scan_prescription(file: UploadFile = File(...)):
    """
    Upload a prescription image.
    scan_graph: validate_upload → extract_with_vlm → normalize_prescription
    """
    prescription = await scan_prescription_upload(file)
    prescription_id = prescription["prescriptionId"]
    prescriptions[prescription_id] = prescription
    save_extracted(prescription_id, prescription.get("medications", []))
    return deepcopy(prescription)


@app.post("/prescriptions/{prescription_id}/confirm")
async def confirm_prescription(prescription_id: str):
    """
    Confirm the extracted drug list.
    confirm_graph: check_confidence → lookup_local_db → [map_vn_to_english → fetch_dailymed]
                   → check_interactions → build_enriched_prescription
    """
    prescription = _get_prescription_or_404(prescription_id)
    raw_medications = prescription.get("medications", [])

    state = await confirm_graph.ainvoke({
        "prescription_id": prescription_id,
        "raw_medications": raw_medications,
        "lookup_results": [],
        "interaction_warnings": [],
        "errors": [],
    })

    enriched = state.get("enriched_medications", raw_medications)
    prescription["medications"] = enriched
    prescription["status"] = "confirmed"
    save_enriched(prescription_id, enriched)

    return ConfirmResponse(
        prescriptionId=prescription_id,
        status="confirmed",
        medications=enriched,
    )


@app.patch("/prescriptions/{prescription_id}/medications/{medication_id}")
async def update_medication(prescription_id: str, medication_id: str, patch: MedicationPatch):
    """Edit a single medication field (user correction before confirmation)."""
    prescription = _get_prescription_or_404(prescription_id)
    medications = prescription.get("medications", [])

    for med in medications:
        if med.get("id") == medication_id:
            if patch.name is not None:
                med["name"] = patch.name
                med["confidence"] = 0.99  # user-edited → high confidence
            if patch.strength is not None:
                med["strength"] = patch.strength
            if patch.dose is not None:
                med["dose"] = patch.dose
            if patch.schedule is not None:
                med["schedule"] = patch.schedule
            if patch.duration is not None:
                med["duration"] = patch.duration
            return {"prescriptionId": prescription_id, "medications": medications}

    raise HTTPException(status_code=404, detail="Medication not found.")


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Q&A turn for an confirmed prescription.
    chat_graph: guard_dangerous_request → detect_intent → build_answer → append_history
    """
    prescription_id = request.prescription_id
    question = (request.question or "").strip()

    if not prescription_id or not question:
        raise HTTPException(status_code=400, detail="prescriptionId and message are required.")

    session = _get_chat_session(prescription_id, prescription_id)
    prescription = get_prescription(prescription_id) or _get_prescription_or_404(prescription_id)
    medications = prescription.get("medications", [])

    state = await chat_graph.ainvoke({
        "prescription_id": prescription_id,
        "question": question,
        "session_id": prescription_id,
        "history": list(session.get("history", [])),
        "medications": medications,
        "errors": [],
    })

    session["history"] = state.get("history", session["history"])

    return ChatResponseFrontend(
        answer=state.get("answer", ""),
        quickReplies=state.get("quick_replies"),
        risk_level=state.get("risk_level", "low"),
    )


class GenerateRemindersRequest(BaseModel):
    leadMinutes: int = 60


@app.post("/prescriptions/{prescription_id}/reminders")
async def generate_reminders(prescription_id: str, request: GenerateRemindersRequest):
    """Generate reminders for a confirmed prescription using the reminders graph."""
    prescription = get_prescription(prescription_id) or _get_prescription_or_404(prescription_id)
    if prescription.get("status") != "confirmed":
        raise HTTPException(
            status_code=400,
            detail="Prescription must be confirmed before generating reminders.",
        )

    state = await reminders_graph.ainvoke({
        "prescription_id": prescription_id,
        "prescription": prescription,
        "leadMinutes": request.leadMinutes,
        "errors": [],
    })

    reminders = state.get("reminders", [])
    return {
        "leadMinutes": request.leadMinutes,
        "reminders": [
            {
                "id": f"rem-{i + 1}",
                "medicationId": item.get("medicationId", ""),
                "label": item.get("label", ""),
                "time": item.get("time", ""),
                "active": True,
            }
            for i, item in enumerate(reminders)
        ],
    }


# ---------------------------------------------------------------------------
# Compatibility endpoint — called by App.jsx after confirm to get enriched drug info
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    prescription_id: str


@app.post("/prescription/analyze")
async def analyze_prescription(request: AnalyzeRequest):
    """
    Return enriched medication data for a confirmed prescription.

    The confirm_graph already resolves and enriches all medications.
    This endpoint just reads that stored result so the frontend can
    merge category_vi, uses_vi, risk_level into its local state.
    """
    prescription = get_prescription(request.prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found.")

    medications = prescription.get("medications") or prescription.get("confirmed_medications") or []
    return {
        "prescription_id": request.prescription_id,
        "medications": medications,
        "summary": f"Đơn thuốc có {len(medications)} thuốc.",
        "high_risk_warnings": [
            f"⚠️ {m.get('raw_name') or m.get('name')}: {', '.join(m.get('safety_flags', []))}"
            for m in medications
            if m.get("risk_level") == "high" and m.get("safety_flags")
        ],
    }


# ---------------------------------------------------------------------------
# Stub endpoints (not graph-driven)
# ---------------------------------------------------------------------------

@app.post("/reminders/bulk")
async def create_reminders_bulk(request: ReminderBulkRequest):
    """Create medication reminders. (stub — returns echo of request)"""
    return {
        "leadMinutes": request.leadMinutes,
        "reminders": [
            {
                "id": f"rem-{i + 1}",
                "medicationId": item.medicationId,
                "label": item.label,
                "time": item.time,
                "active": True,
            }
            for i, item in enumerate(request.items)
        ],
    }


@app.get("/specialists")
async def get_specialists(prescriptionId: str = ""):
    """Return a list of available specialists. (stub)"""
    return [
        {
            "id": "sp-1",
            "name": "BS. Phạm Thị Lan",
            "specialty": "Nội tiết",
            "location": "Phòng khám C3",
            "nextSlot": "2026-06-05T09:00:00+07:00",
        },
        {
            "id": "sp-2",
            "name": "DS. Nguyễn Minh Tuấn",
            "specialty": "Tư vấn dược",
            "location": "Tư vấn trực tuyến",
            "nextSlot": "2026-06-06T14:00:00+07:00",
        },
    ]


@app.post("/appointments")
async def create_appointment(payload: AppointmentRequest):
    """Book an appointment with a specialist. (stub)"""
    return {
        "id": f"apt-{uuid.uuid4().hex[:8]}",
        "specialistId": payload.specialistId,
        "slot": payload.slot,
        "status": "confirmed",
    }
