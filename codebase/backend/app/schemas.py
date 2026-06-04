"""Pydantic schemas for MedChat API."""
from typing import Optional, List
from pydantic import BaseModel


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
    safety_notice: str
