from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# Patient Schemas
class PatientBase(BaseModel):
    patient_code: str = Field(..., description="Unique simulated patient identifier")
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


# Observation Schemas
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
    patient_id: int


class ObservationRead(ObservationBase):
    id: int
    patient_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# Assessment and Escalation Schemas
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


class EscalationBase(BaseModel):
    risk_level: str
    reason: str
    recommendation: str


class EscalationCreate(EscalationBase):
    patient_id: int
    observation_id: int


class EscalationRead(EscalationBase):
    id: int
    patient_id: int
    observation_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
