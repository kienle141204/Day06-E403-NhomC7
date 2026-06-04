import os
from copy import deepcopy
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agent import answer_medication_question
from .mock_data import SPECIALISTS, initial_prescription_store


load_dotenv()

app = FastAPI(title="MedChat Medication API")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prescriptions = initial_prescription_store()
chat_sessions: dict[str, dict] = {}
last_scanned_index = 0


class MedicationPatch(BaseModel):
    name: str | None = None
    strength: str | None = None
    dose: str | None = None
    schedule: str | None = None
    duration: str | None = None


class ChatRequest(BaseModel):
    prescriptionId: str
    message: str
    sessionId: str | None = None


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


def get_prescription_or_404(prescription_id: str) -> dict:
    prescription = prescriptions.get(prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found.")
    return prescription


def get_chat_session(session_id: str, prescription_id: str) -> dict:
    session = chat_sessions.setdefault(
        session_id,
        {
            "prescriptionId": prescription_id,
            "history": [],
        },
    )
    if session["prescriptionId"] != prescription_id:
        raise HTTPException(
            status_code=409,
            detail="This chat session is already locked to another prescription.",
        )
    return session


def append_chat_history(session: dict, user_message: str, assistant_message: str) -> None:
    session["history"].extend(
        [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ]
    )
    session["history"] = session["history"][-12:]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/prescriptions")
def list_prescriptions():
    return [
        {
            "prescriptionId": item["prescriptionId"],
            "doctorName": item["doctorName"],
            "clinic": item["clinic"],
            "issuedAt": item["issuedAt"],
            "status": item["status"],
            "medicationCount": len(item["medications"]),
        }
        for item in prescriptions.values()
    ]


@app.get("/prescriptions/{prescription_id}")
def get_prescription(prescription_id: str):
    return deepcopy(get_prescription_or_404(prescription_id))


@app.post("/prescriptions/scan")
async def scan_prescription(file: UploadFile | None = File(default=None)):
    global last_scanned_index

    items = list(prescriptions.values())
    if not items:
        raise HTTPException(status_code=404, detail="No mock prescriptions available.")

    prescription = items[last_scanned_index % len(items)]
    last_scanned_index += 1
    prescription["status"] = "pending"
    return deepcopy(prescription)


@app.patch("/prescriptions/{prescription_id}/medications/{medication_id}")
def update_medication(prescription_id: str, medication_id: str, patch: MedicationPatch):
    prescription = get_prescription_or_404(prescription_id)
    updates = patch.model_dump(exclude_none=True)
    for medication in prescription["medications"]:
        if medication["id"] == medication_id:
            medication.update(updates)
            medication["confidence"] = 0.99
            return deepcopy(prescription)
    raise HTTPException(status_code=404, detail="Medication not found.")


@app.post("/prescriptions/{prescription_id}/confirm")
def confirm_prescription(prescription_id: str):
    prescription = get_prescription_or_404(prescription_id)
    prescription["status"] = "confirmed"
    return deepcopy(prescription)


@app.post("/chat")
def chat(request: ChatRequest):
    prescription = get_prescription_or_404(request.prescriptionId)
    if prescription.get("status") != "confirmed":
        raise HTTPException(status_code=400, detail="Confirm prescription before chatting.")
    session_id = request.sessionId or request.prescriptionId
    session = get_chat_session(session_id, request.prescriptionId)
    result = answer_medication_question(
        deepcopy(prescription),
        request.message,
        history=session["history"],
    )
    append_chat_history(session, request.message, result["answer"])
    return {**result, "sessionId": session_id}


@app.post("/reminders/bulk")
def create_reminders(request: ReminderBulkRequest):
    get_prescription_or_404(request.prescriptionId)
    return {
        "leadMinutes": request.leadMinutes,
        "reminders": [
            {
                "id": f"rem-{index + 1}",
                "medicationId": item.medicationId,
                "label": item.label,
                "time": item.time,
                "active": True,
            }
            for index, item in enumerate(request.items)
        ],
    }


@app.get("/specialists")
def get_specialists(prescriptionId: str | None = None):
    if prescriptionId:
        get_prescription_or_404(prescriptionId)
    return deepcopy(SPECIALISTS)


@app.post("/appointments")
def create_appointment(request: AppointmentRequest):
    if request.prescriptionId:
        get_prescription_or_404(request.prescriptionId)
    matching = next((item for item in SPECIALISTS if item["id"] == request.specialistId), None)
    if not matching:
        raise HTTPException(status_code=404, detail="Specialist not found.")
    return {
        "id": f"apt-{uuid4().hex[:8]}",
        "specialistId": request.specialistId,
        "slot": request.slot,
        "status": "confirmed",
    }
