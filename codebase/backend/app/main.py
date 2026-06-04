"""FastAPI main application for MedChat backend."""
import uuid
from copy import deepcopy
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import from local services
from app.schemas import (
    MedicationInput,
    ExtractDemoResponse,
    ConfirmRequest,
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse
)
from app.services import (
    save_extracted,
    save_confirmed,
    save_analysis,
    get_prescription,
    analyze_prescription,
    get_drug_data_service
)

# Import from remote branch modules (if available)
try:
    from .agent import answer_medication_question
    HAS_AGENT = True
except ImportError:
    HAS_AGENT = False

try:
    from .graphs.prescription_scan import scan_prescription_upload
    HAS_VISION = True
except ImportError:
    HAS_VISION = False

try:
    from .mock_data import SPECIALISTS, initial_prescription_store
    HAS_MOCK = True
except ImportError:
    HAS_MOCK = False


app = FastAPI(
    title="MedChat API",
    description="Healthcare chatbot backend for prescription analysis",
    version="1.0.0"
)

# CORS for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores
prescriptions = {}
chat_sessions: dict[str, dict] = {}


# === Request/Response Models ===

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


# === Helper Functions ===

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
        }
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


# === Endpoints ===

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MedChat API"}


@app.post("/prescriptions/scan")
async def scan_prescription(file: UploadFile | None = File(default=None)):
    """
    Scan prescription from uploaded file.
    If file provided and vision module available, uses vision.
    Otherwise returns mock medications for demo.
    """
    prescription_id = str(uuid.uuid4())
    
    # Mock medications for demo (matches frontend expectations)
    medications = [
        {
            "id": "med_1",
            "name": "Aerius 5mg",
            "strength": "5mg",
            "dose": "1 viên",
            "schedule": "ngày 1 lần",
            "duration": "5 ngày",
            "risk": "normal",
            "confidence": 0.92
        },
        {
            "id": "med_2",
            "name": "Augmentin 625mg",
            "strength": "625mg",
            "dose": "1 viên",
            "schedule": "ngày 2 lần",
            "duration": "5 ngày",
            "risk": "normal",
            "confidence": 0.89
        },
        {
            "id": "med_3",
            "name": "Cetirizine 10mg",
            "strength": "10mg",
            "dose": "1 viên",
            "schedule": "khi cần",
            "duration": "3 ngày",
            "risk": "normal",
            "confidence": 0.91
        }
    ]
    
    # Save to stores
    prescriptions[prescription_id] = {
        "prescriptionId": prescription_id,
        "confidence": 0.90,
        "doctorName": "BS. Demo",
        "clinic": "Phòng khám Demo",
        "issuedAt": "2026-06-04",
        "status": "pending",
        "medications": medications,
        "warnings": []
    }
    
    # Also save to prescription store service
    save_extracted(prescription_id, medications)
    
    return deepcopy(prescriptions[prescription_id])


class ConfirmResponse(BaseModel):
    prescriptionId: str
    status: str
    medications: list


@app.post("/prescriptions/{prescription_id}/confirm")
async def confirm_prescription(prescription_id: str):
    """
    Confirm prescription (frontend expects this format).
    """
    prescription = prescriptions.get(prescription_id)
    if not prescription:
        # Try from prescription store service
        prescription = get_prescription(prescription_id)
        if not prescription:
            raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Save confirmed status
    prescription["status"] = "confirmed"
    save_confirmed(prescription_id, prescription.get("medications", []))
    
    return ConfirmResponse(
        prescriptionId=prescription_id,
        status="confirmed",
        medications=prescription.get("medications", [])
    )


@app.patch("/prescriptions/{prescription_id}/medications/{medication_id}")
async def update_medication(
    prescription_id: str, 
    medication_id: str, 
    patch: MedicationPatch
):
    """
    Update medication details (frontend expects this format).
    """
    prescription = prescriptions.get(prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    medications = prescription.get("medications", [])
    updated = False
    
    for med in medications:
        if med.get("id") == medication_id:
            if patch.name is not None:
                med["name"] = patch.name
            if patch.strength is not None:
                med["strength"] = patch.strength
            if patch.dose is not None:
                med["dose"] = patch.dose
            if patch.schedule is not None:
                med["schedule"] = patch.schedule
            if patch.duration is not None:
                med["duration"] = patch.duration
            updated = True
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    # Save updated medications
    save_confirmed(prescription_id, medications)
    
    return {
        "prescriptionId": prescription_id,
        "medications": medications
    }


class ChatResponseFrontend(BaseModel):
    answer: str
    quickReplies: Optional[list] = None
    risk_level: Optional[str] = None


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint matching frontend format.
    Uses deterministic responses based on question keywords.
    """
    prescription = prescriptions.get(request.prescriptionId)
    if not prescription:
        prescription = get_prescription(request.prescriptionId)
    
    if not prescription:
        return ChatResponseFrontend(
            answer="Không tìm thấy đơn thuốc. Vui lòng bắt đầu lại.",
            quickReplies=None
        )
    
    analysis = prescription.get("analysis")
    question_lower = request.message.lower()
    medications = analysis.get("medications", []) if analysis else prescription.get("medications", [])
    
    quick_replies = None
    answer = ""
    
    # Handle specific question types
    if "buồn ngủ" in question_lower or " ngủ" in question_lower or "tác dụng phụ" in question_lower:
        answer = _handle_side_effects(medications)
        quick_replies = ['Lịch uống trong ngày', 'Hỏi về thuốc', 'Tạo nhắc uống thuốc']
    elif any(kw in question_lower for kw in ["uống gấp đôi", "tăng liều", "giảm liều", "ngưng", "tang lieu", "giam lieu", "ngung thuoc"]):
        answer = "Mình không thể thay bác sĩ quyết định đổi liều hoặc ngừng thuốc. Hãy liên hệ bác sĩ để được tư vấn trực tiếp. Việc tự ý thay đổi liều có thể gây nguy hiểm."
        quick_replies = ['Giải thích từng thuốc', 'Lịch uống trong ngày', 'Đặt lịch với bác sĩ']
    elif "nhắc" in question_lower or "lịch" in question_lower or "uống thuốc" in question_lower:
        answer = _handle_reminder_question(medications)
        quick_replies = ['Tạo tất cả nhắc nhở', 'Chỉ nhắc buổi tối']
    else:
        answer = _handle_general_question(medications)
        quick_replies = ['Tác dụng phụ?', 'Lịch uống trong ngày', 'Tạo nhắc uống thuốc']
    
    return ChatResponseFrontend(
        answer=answer,
        quickReplies=quick_replies
    )


def _handle_side_effects(medications: list) -> str:
    """Handle questions about side effects."""
    side_effect_info = []
    
    for med in medications:
        name = med.get("name", "Unknown")
        notes = med.get("important_notes_vi", [])
        
        if not notes:
            notes = med.get("important_notes", [])
        
        notes_text = " ".join(notes).lower() if notes else ""
        
        category = med.get("category_vi", "") or ""
        
        if "kháng sinh" in category.lower():
            side_effect_info.append(f"{name}: Có thể gây tiêu chảy, buồn nôn hoặc dị ứng da.")
        elif "chống dị ứng" in category.lower() or "kháng histamine" in category.lower():
            side_effect_info.append(f"{name}: Có thể gây buồn ngủ nhẹ.")
        elif "hạ sốt" in category.lower() or "giảm đau" in category.lower():
            side_effect_info.append(f"{name}: An toàn khi dùng đúng liều, tránh dùng quá liều.")
    
    if side_effect_info:
        return "Thông tin về tác dụng phụ:\n" + "\n".join(f"• {info}" for info in side_effect_info)
    return "Trong đơn thuốc hiện tại, các thuốc được liệt kê thường có tác dụng phụ nhẹ. Tuy nhiên, mỗi người có thể phản ứng khác nhau với thuốc."


def _handle_reminder_question(medications: list) -> str:
    """Handle questions about reminders."""
    reminder_info = []
    
    for med in medications:
        name = med.get("name", "Unknown")
        schedule = med.get("schedule", med.get("frequency", ""))
        duration = med.get("duration", "")
        
        if schedule and schedule not in ["khi cần", "khi can"]:
            reminder_info.append(f"• {name}: {schedule} ({duration})")
        elif schedule in ["khi cần", "khi can"]:
            reminder_info.append(f"• {name}: Chỉ uống khi cần, không cần nhắc định kỳ")
    
    if reminder_info:
        return "Tôi có thể tạo nhắc cho các thuốc sau:\n" + "\n".join(reminder_info)
    return "Không có thuốc nào cần nhắc định kỳ trong đơn này."


def _handle_general_question(medications: list) -> str:
    """Handle general questions about medications."""
    med_info = []
    
    for med in medications:
        name = med.get("name", "Unknown")
        schedule = med.get("schedule", med.get("frequency", "Không rõ"))
        duration = med.get("duration", "")
        found = med.get("found", True)
        
        if found:
            uses = med.get("uses_vi", [])
            if uses and isinstance(uses, list):
                use_text = uses[0] if uses else "Thuốc theo đơn bác sĩ."
                med_info.append(f"• {name}: {use_text}")
            else:
                med_info.append(f"• {name}: Thuốc theo đơn ({schedule}, {duration})")
        else:
            med_info.append(f"• {name}: Thuốc trong đơn ({schedule}, {duration})")
    
    if med_info:
        return "Theo đơn đã xác nhận:\n" + "\n".join(med_info) + "\n\nThông tin chỉ mang tính tham khảo về thuốc."
    return "Không có thông tin về thuốc trong đơn."


# === Analysis Endpoint ===

@app.post("/prescription/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Analyze a prescription and return medication details with risk assessment.
    Uses local drug database.
    """
    analysis = analyze_prescription(request.prescription_id)
    
    # Save analysis to both stores
    save_analysis(request.prescription_id, analysis)
    if request.prescription_id in prescriptions:
        prescriptions[request.prescription_id]["analysis"] = analysis
    
    return AnalyzeResponse(**analysis)


@app.post("/prescription/extract-demo")
async def extract_demo():
    """
    Extract demo prescription (legacy endpoint for testing).
    """
    prescription_id = str(uuid.uuid4())
    
    medications = [
        MedicationInput(
            id="med_1",
            raw_name="Aerius 5mg",
            dosage="1 viên",
            frequency="ngày 1 lần",
            duration="5 ngày"
        ),
        MedicationInput(
            id="med_2",
            raw_name="Augmentin 625mg",
            dosage="1 viên",
            frequency="ngày 2 lần",
            duration="5 ngày"
        ),
        MedicationInput(
            id="med_3",
            raw_name="Cetirizin 10mg",
            dosage="1 viên",
            frequency="khi cần",
            duration="3 ngày"
        )
    ]
    
    save_extracted(prescription_id, [med.model_dump() for med in medications])
    
    return ExtractDemoResponse(
        prescription_id=prescription_id,
        status="extracted",
        medications=medications
    )


# === Reminders & Specialists Endpoints ===

@app.post("/reminders/bulk")
async def create_reminders_bulk(request: ReminderBulkRequest):
    """Create medication reminders."""
    return {
        "leadMinutes": request.leadMinutes,
        "reminders": [
            {
                "id": f"rem-{i+1}",
                "medicationId": item.medicationId,
                "label": item.label,
                "time": item.time,
                "active": True
            }
            for i, item in enumerate(request.items)
        ]
    }


@app.get("/specialists")
async def get_specialists(prescriptionId: str = ""):
    """Get list of specialists."""
    return [
        {
            "id": "sp-1",
            "name": "BS. Phạm Thị Lan",
            "specialty": "Nội tiết",
            "location": "Phòng khám C3",
            "nextSlot": "2026-06-05T09:00:00+07:00"
        },
        {
            "id": "sp-2",
            "name": "DS. Nguyễn Minh Tuấn",
            "specialty": "Tư vấn dược",
            "location": "Tư vấn trực tuyến",
            "nextSlot": "2026-06-06T14:00:00+07:00"
        }
    ]


@app.post("/appointments")
async def create_appointment(payload: AppointmentRequest):
    """Create appointment with specialist."""
    return {
        "id": f"apt-{uuid.uuid4().hex[:8]}",
        "specialistId": payload.specialistId,
        "slot": payload.slot,
        "status": "confirmed"
    }
