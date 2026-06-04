"""Pydantic schemas for MedChat API."""
from datetime import date
from typing import Literal, Optional, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


RiskLevel = Literal["normal", "medium", "high"]
WarningLevel = Literal["low", "medium", "high"]


# === Frontend-compatible models ===

class Medication(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    strength: str = ""
    dose: str = ""
    schedule: str = ""
    duration: str = ""
    risk: RiskLevel = "normal"
    confidence: float = Field(default=0.7, ge=0, le=1)
    notes: str = ""

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Medication name is required.")
        return value


class PrescriptionWarning(BaseModel):
    id: str
    level: WarningLevel = "medium"
    title: str
    detail: str


class Prescription(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prescriptionId: str
    confidence: float = Field(default=0.7, ge=0, le=1)
    doctorName: str = "Unknown doctor"
    clinic: str = "Unknown clinic"
    issuedAt: str = Field(default_factory=lambda: date.today().isoformat())
    status: Literal["pending", "confirmed"] = "pending"
    medications: list[Medication]
    warnings: list[PrescriptionWarning] = Field(default_factory=list)


# === Vision models ===

class VisionMedication(BaseModel):
    name: str = ""
    strength: str = ""
    dose: str = ""
    schedule: str = ""
    duration: str = ""
    confidence: float = Field(default=0.7, ge=0, le=1)
    notes: str = ""


class VisionPrescriptionResult(BaseModel):
    is_valid_prescription: bool = False
    confidence: float = Field(default=0, ge=0, le=1)
    doctor_name: str = ""
    clinic: str = ""
    issued_at: str = ""
    medications: list[VisionMedication] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason: str = ""


# === Internal API models ===

class MedicationInput(BaseModel):
    id: Optional[str] = None
    raw_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    note: Optional[str] = None


class ExtractDemoResponse(BaseModel):
    prescription_id: str
    status: str
    medications: List[MedicationInput]


class ConfirmRequest(BaseModel):
    prescription_id: str
    medications: List[MedicationInput]


class ResolvedMedication(BaseModel):
    raw_name: str
    found: bool
    source: Optional[str] = None
    matched_name: Optional[str] = None
    ingredient_vi: Optional[str] = None
    ingredient_en: Optional[str] = None
    category_vi: Optional[str] = None
    uses_vi: Optional[List[str]] = None
    important_notes_vi: Optional[List[str]] = None
    source_urls: Optional[List[dict]] = None
    confidence: Optional[float] = None
    needs_review: bool = False
    risk_level: str = "low"
    safety_flags: List[str] = []
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None


class AnalyzeRequest(BaseModel):
    prescription_id: str


class AnalyzeResponse(BaseModel):
    prescription_id: str
    summary: str
    medications: List[ResolvedMedication]
    high_risk_warnings: List[str]
    safety_notice: str


class ChatRequest(BaseModel):
    prescription_id: str
    question: str


class ChatResponse(BaseModel):
    answer: str
    risk_level: str
    intent: str
    related_medications: list[str] = []
    safety_notice: str