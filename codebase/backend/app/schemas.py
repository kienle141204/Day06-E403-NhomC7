from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RiskLevel = Literal["normal", "medium", "high"]
WarningLevel = Literal["low", "medium", "high"]


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
