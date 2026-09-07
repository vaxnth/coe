from datetime import datetime, date
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------
# Patient Schemas
# ---------------------------------------------------------
class PatientBase(BaseModel):
    patient_code: str = Field(..., description="Unique simulated patient identifier (e.g. PAT-001)")
    name: str = Field(..., description="Simulated patient name")
    age: int = Field(..., ge=0, le=130, description="Patient age in years")
    surgery_type: str = Field(..., description="Type of surgical procedure performed")
    surgery_date: date = Field(..., description="Date of surgery")


class PatientCreate(PatientBase):
    pass


class PatientRead(PatientBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Observation Schemas
# ---------------------------------------------------------
class ObservationBase(BaseModel):
    temperature: Optional[float] = Field(
        None,
        description="Body temperature in Celsius (None if sensor is missing)"
    )
    pain_score: int = Field(
        ...,
        ge=0,
        le=10,
        description="Patient-reported pain score from 0 (none) to 10 (worst)"
    )
    wound_status: str = Field(
        ...,
        description="Observed wound status: Normal, Redness, Swelling, Discharge, Bleeding, Unknown"
    )
    symptom_description: Optional[str] = Field(
        None,
        description="Patient-reported qualitative symptom description"
    )
    sensor_status: str = Field(
        ...,
        description="Temperature sensor status: Normal, Noisy, Missing"
    )


class ObservationCreate(ObservationBase):
    patient_id: Optional[int] = Field(None, description="Database ID of the patient")
    patient_code: Optional[str] = Field(None, description="Patient code if ID is not known")


class ObservationRead(ObservationBase):
    id: int
    patient_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Assessment Schemas
# ---------------------------------------------------------
class AssessmentResult(BaseModel):
    risk_level: str = Field(
        ...,
        description="Evaluated risk level: LOW, MEDIUM, HIGH, CONFLICT"
    )
    reason: str = Field(
        ...,
        description="Transparent explanation of why the risk level was assigned"
    )
    recommendation: str = Field(
        ...,
        description="Non-diagnostic, actionable escalation advice for clinical personnel"
    )
    observation_id: Optional[int] = None
    escalation_id: Optional[int] = None


class ObservationAssessmentDetail(BaseModel):
    observation_id: int
    patient_id: int
    patient_code: str
    temperature: Optional[float]
    pain_score: int
    wound_status: str
    symptom_description: Optional[str]
    sensor_status: str
    timestamp: datetime
    risk_level: str
    reason: str
    recommendation: str
    escalation_status: Optional[str] = None  # None, OPEN, IN_PROGRESS, RESOLVED
    escalation_id: Optional[int] = None
    assigned_staff: Optional[str] = None
    due_date: Optional[datetime] = None


# ---------------------------------------------------------
# Escalation Schemas (Phase 8)
# ---------------------------------------------------------
class EscalationBase(BaseModel):
    risk_level: str = Field(..., description="HIGH or CONFLICT")
    reason: str = Field(..., description="Clinical triage rationale")
    recommendation: str = Field(..., description="Clinical review action")
    status: str = Field(default="OPEN", description="OPEN, IN_PROGRESS, RESOLVED")
    assigned_staff: Optional[str] = Field(None, description="Staff/clinician name assigned to case")
    due_date: Optional[datetime] = Field(None, description="Target completion timestamp for follow-up")


class EscalationCreate(EscalationBase):
    patient_id: int
    observation_id: int


class EscalationStatusUpdate(BaseModel):
    status: str = Field(..., description="Target status: OPEN, IN_PROGRESS, or RESOLVED")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        upper = v.strip().upper()
        if upper not in {"OPEN", "IN_PROGRESS", "RESOLVED"}:
            raise ValueError("Status must be one of: 'OPEN', 'IN_PROGRESS', 'RESOLVED'")
        return upper


class EscalationAssignUpdate(BaseModel):
    assigned_staff: str = Field(..., min_length=1, description="Assigned clinician or staff name")


class EscalationDueDateUpdate(BaseModel):
    due_date: Optional[datetime] = Field(..., description="Follow-up deadline")


class EscalationRead(EscalationBase):
    id: int
    patient_id: int
    observation_id: int
    patient_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
