"""FastAPI main application for MedChat backend."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import uuid
from copy import deepcopy
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

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
    get_drug_data_service,
    answer_question
)

# Import from remote branch modules (if available)
try:
    from .agent import answer_medication_question
    HAS_AGENT = True
except ImportError:
    HAS_AGENT = False

try:
    from .vision import extract_prescription_from_image
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

def _get_mime_type(filename: str) -> str:
    """Get MIME type from filename extension."""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    mime_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
        'gif': 'image/gif',
        'bmp': 'image/bmp'
    }
    return mime_types.get(ext, 'image/jpeg')


def _convert_vision_to_medication(vision_med, index: int) -> dict:
    """Convert VisionMedication to frontend Medication format."""
    return {
        "id": f"med_{index + 1}",
        "name": vision_med.name if hasattr(vision_med, 'name') else vision_med.get("name", ""),
        "strength": vision_med.strength if hasattr(vision_med, 'strength') else vision_med.get("strength", ""),
        "dose": vision_med.dose if hasattr(vision_med, 'dose') else vision_med.get("dose", ""),
        "schedule": vision_med.schedule if hasattr(vision_med, 'schedule') else vision_med.get("schedule", ""),
        "duration": vision_med.duration if hasattr(vision_med, 'duration') else vision_med.get("duration", ""),
        "risk": "normal",
        "confidence": vision_med.confidence if hasattr(vision_med, 'confidence') else vision_med.get("confidence", 0.7),
        "notes": vision_med.notes if hasattr(vision_med, 'notes') else vision_med.get("notes", "")
    }


def _convert_vision_result(result, prescription_id: str) -> dict:
    """Convert VisionPrescriptionResult to frontend Prescription format."""
    medications = [
        _convert_vision_to_medication(med, i)
        for i, med in enumerate(result.medications)
    ]
    
    warnings = []
    if result.warnings:
        for i, warning in enumerate(result.warnings):
            warning_text = warning if isinstance(warning, str) else str(warning)
            warnings.append({
                "id": f"warn_{i + 1}",
                "level": "medium",
                "title": "Canh bao",
                "detail": warning_text
            })
    
    return {
        "prescriptionId": prescription_id,
        "confidence": result.confidence,
        "doctorName": result.doctor_name or "Chưa xác định",
        "clinic": result.clinic or "Chưa xác định",
        "issuedAt": result.issued_at,
        "status": "pending",
        "medications": medications,
        "warnings": warnings,
        "is_valid_prescription": result.is_valid_prescription,
        "reason": result.reason
    }


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
    Scan prescription - extracts medications using vision OCR.
    If file is provided, uses OpenAI vision model to extract medications.
    Otherwise returns mock medications for demo.
    """
    prescription_id = str(uuid.uuid4())
    drug_service = get_drug_data_service()
    
    # Try to extract from uploaded image using vision OCR
    if file and file.filename:
        filename_lower = file.filename.lower()
        
        # Check if file is an image
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp')
        is_image = any(filename_lower.endswith(ext) for ext in image_extensions)
        
        if is_image and HAS_VISION:
            try:
                # Read file content and convert to base64
                contents = await file.read()
                import base64
                image_base64 = base64.b64encode(contents).decode('utf-8')
                mime_type = _get_mime_type(file.filename)
                
                # Use vision model to extract prescription
                vision_result = await extract_prescription_from_image(image_base64, mime_type)
                
                # Check if valid prescription
                if not vision_result.is_valid_prescription:
                    return {
                        "error": "not_prescription",
                        "message": vision_result.reason or "Ảnh không phải là đơn thuốc hợp lệ.",
                        "prescriptionId": prescription_id,
                        "status": "rejected"
                    }
                
                # Convert vision result to prescription format
                prescription_data = _convert_vision_result(vision_result, prescription_id)
                prescriptions[prescription_id] = prescription_data
                save_extracted(prescription_id, prescription_data.get("medications", []))
                
                return prescription_data
                
            except HTTPException:
                raise
            except Exception as exc:
                # Fallback to demo data if vision fails
                medications = _get_demo_medications_with_lookup(drug_service)
                warnings = [{
                    "id": "warn_fallback",
                    "level": "medium",
                    "title": "OCR Demo Mode",
                    "detail": f"Khong the quet anh ({str(exc)}). Hien thi du lieu demo."
                }]
                prescriptions[prescription_id] = {
                    "prescriptionId": prescription_id,
                    "confidence": 0.90,
                    "doctorName": "BS. Demo",
                    "clinic": "Phong kham Demo",
                    "issuedAt": "2026-06-04",
                    "status": "pending",
                    "medications": medications,
                    "warnings": warnings
                }
                save_extracted(prescription_id, medications)
                return deepcopy(prescriptions[prescription_id])
        else:
            # Non-image file or vision not available, try filename matching
            medications = _extract_from_filename(filename_lower, drug_service)
            if not medications:
                medications = _get_demo_medications_with_lookup(drug_service)
    else:
        # No file, use demo medications with local database lookup
        medications = _get_demo_medications_with_lookup(drug_service)
    
    # Save to prescriptions store
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


def _extract_from_filename(filename: str, drug_service) -> list | None:
    """Extract drug names from filename using local database."""
    import re
    # Remove extension and common prefixes
    clean_name = re.sub(r'\.(jpg|jpeg|png|pdf|webp)$', '', filename, flags=re.IGNORECASE)
    clean_name = re.sub(r'^(don|prescription|donthuoc|img|image|photo|pic|capture|screenshot)[\s_-]*', '', clean_name)
    
    # Try to match individual words against drug database
    words = re.split(r'[\s_-]+', clean_name)
    potential_names = []
    
    for word in words:
        if len(word) >= 3:
            result = drug_service.resolve_local_drug(word)
            if result["found"] or result["needs_review"]:
                matched = result["matched_item"]
                if matched:
                    potential_names.append(matched.get("ingredient_vi") or word)
    
    if potential_names:
        return [
            {
                "id": f"med_{i+1}",
                "name": name,
                "strength": "Xem đơn",
                "dose": "Xem đơn",
                "schedule": "Theo chỉ định",
                "duration": "Theo đơn",
                "risk": "normal",
                "confidence": 0.85
            }
            for i, name in enumerate(potential_names[:5])
        ]
    return None


def _get_demo_medications():
    """Return demo medications for testing."""
    return [
        {
            "id": "med_1",
            "name": "Desloratadine 5mg",
            "strength": "5mg",
            "dose": "1 viên",
            "schedule": "ngày 1 lần",
            "duration": "5 ngày",
            "risk": "normal",
            "confidence": 0.92
        },
        {
            "id": "med_2",
            "name": "Amoxicillin 500mg",
            "strength": "500mg",
            "dose": "1 viên",
            "schedule": "ngày 3 lần",
            "duration": "7 ngày",
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


def _get_demo_medications_with_lookup(drug_service):
    """Return demo medications with info from local database."""
    demo_names = ["Desloratadine", "Amoxicillin", "Cetirizine"]
    medications = []
    
    for i, name in enumerate(demo_names):
        result = drug_service.resolve_local_drug(name)
        matched = result.get("matched_item", {})
        
        med = {
            "id": f"med_{i+1}",
            "name": name + " 5mg",
            "strength": "5mg",
            "dose": "1 viên",
            "schedule": "ngày 1 lần",
            "duration": "5 ngày",
            "risk": "normal",
            "confidence": result.get("confidence", 0.9)
        }
        
        if matched.get("category_vi"):
            med["category_vi"] = matched["category_vi"]
        
        medications.append(med)
    
    return medications


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


class ChatRequest(BaseModel):
    prescription_id: Optional[str] = Field(default=None, alias="prescriptionId")
    question: Optional[str] = Field(default=None, alias="message")

    model_config = ConfigDict(populate_by_name=True)


class ChatResponseFrontend(BaseModel):
    answer: str
    quickReplies: Optional[list] = None
    risk_level: Optional[str] = None


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint using deterministic chat service.
    Accepts both internal schema (prescription_id + question) and
    frontend schema (prescriptionId + message).
    """
    prescription_id = request.prescription_id
    question = request.question

    if not prescription_id or not question or not question.strip():
        raise HTTPException(status_code=400, detail="prescription_id and question are required")

    result = answer_question(prescription_id, question.strip())

    return ChatResponseFrontend(
        answer=result["answer"],
        quickReplies=None,
        risk_level=result["risk_level"]
    )


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
