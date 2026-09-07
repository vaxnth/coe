from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Date,
    ForeignKey
)
from sqlalchemy.orm import relationship

from .database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    surgery_type = Column(String(100), nullable=False)
    surgery_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    observations = relationship(
        "Observation",
        back_populates="patient",
        cascade="all, delete-orphan"
    )
    escalations = relationship(
        "Escalation",
        back_populates="patient",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Patient(code='{self.patient_code}', name='{self.name}', surgery='{self.surgery_type}')>"


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    temperature = Column(Float, nullable=True)  # Nullable to accommodate missing sensor readings
    pain_score = Column(Integer, nullable=False)
    wound_status = Column(String(50), nullable=False)
    symptom_description = Column(Text, nullable=True)
    sensor_status = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="observations")
    escalation = relationship(
        "Escalation",
        back_populates="observation",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<Observation(id={self.id}, patient_id={self.patient_id}, "
            f"temp={self.temperature}, pain={self.pain_score}, wound='{self.wound_status}')>"
        )


class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    observation_id = Column(Integer, ForeignKey("observations.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_level = Column(String(20), nullable=False)
    reason = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    status = Column(String(20), default="OPEN", nullable=False)  # Allowed: OPEN, IN_PROGRESS, RESOLVED
    assigned_staff = Column(String(100), nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="escalations")
    observation = relationship("Observation", back_populates="escalation")

    def __repr__(self):
        return (
            f"<Escalation(id={self.id}, patient_id={self.patient_id}, "
            f"risk='{self.risk_level}', status='{self.status}')>"
        )
