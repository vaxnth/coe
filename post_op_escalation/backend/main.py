import os
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import get_db, create_tables
from .models import Patient, Observation, Escalation
from .schemas import (
    PatientCreate,
    PatientRead,
    ObservationCreate,
    ObservationRead,
    AssessmentResult,
    ObservationAssessmentDetail,
    EscalationBase,
    EscalationCreate,
    EscalationRead,
    EscalationStatusUpdate,
    EscalationAssignUpdate,
    EscalationDueDateUpdate,
)
from .rules import evaluate_observation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist on startup
    create_tables()
    yield


app = FastAPI(
    title="Post-Operative Escalation Prototype API",
    description=(
        "Field-ready decision-support backend for post-operative patient vital triage, "
        "transparent rule-based risk evaluation, and clinical escalation management. "
        "Academic prototype — provides decision support only, not medical diagnoses."
    ),
    version="0.7.0",
    lifespan=lifespan
)

# CORS middleware for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Mount static files if frontend directory exists
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ----------------------------------------------------------------------
# 1. System Health & Metadata Endpoints
# ----------------------------------------------------------------------
@app.get("/", tags=["System"])
def get_root():
    """
    Return application status, current milestone, and mandatory safety notice.
    """
    return {
        "status": "online",
        "app_title": "A Field-Ready Prototype for Post-Operative Patients Reporting Pain, Temperature & Wound Observations",
        "project_completion": "70%",
        "implemented_phases": [
            "Phase 1 - Project Foundation",
            "Phase 2 - Database Architecture",
            "Phase 3 - Simulated Data Generator",
            "Phase 4 - Rule-Based Risk Engine",
            "Phase 5 - FastAPI Backend & REST APIs",
            "Phase 6 - Patient Web Interface",
            "Phase 7 - Clinician Dashboard",
            "Phase 8 - Escalation & Follow-Up Tracking"
        ],
        "safety_disclaimer": (
            "This system provides decision support only. "
            "Final decisions remain with clinicians or authorized staff."
        )
    }


@app.get("/health", tags=["System"])
def get_health(db: Session = Depends(get_db)):
    """
    Check backend health and verify active PostgreSQL database connectivity.
    """
    try:
        # Ping PostgreSQL
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity failure: {str(e)}"
        )


# ----------------------------------------------------------------------
# 2. Patient Management Endpoints
# ----------------------------------------------------------------------
@app.post("/patients", response_model=PatientRead, status_code=status.HTTP_201_CREATED, tags=["Patients"])
def create_patient(patient_in: PatientCreate, db: Session = Depends(get_db)):
    """
    Create a simulated patient record in PostgreSQL.
    """
    existing = db.query(Patient).filter(Patient.patient_code == patient_in.patient_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient with code '{patient_in.patient_code}' already exists."
        )

    patient = Patient(
        patient_code=patient_in.patient_code,
        name=patient_in.name,
        age=patient_in.age,
        surgery_type=patient_in.surgery_type,
        surgery_date=patient_in.surgery_date
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@app.get("/patients", response_model=List[PatientRead], tags=["Patients"])
def get_patients(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    """
    Retrieve list of simulated patients.
    """
    return db.query(Patient).order_by(Patient.patient_code.asc()).limit(limit).all()


@app.get("/patients/{patient_id}", response_model=PatientRead, tags=["Patients"])
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details of a single simulated patient.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} was not found."
        )
    return patient


# ----------------------------------------------------------------------
# 3. Patient Observations Endpoints
# ----------------------------------------------------------------------
@app.post("/observations", response_model=ObservationRead, status_code=status.HTTP_201_CREATED, tags=["Observations"])
def submit_observation(obs_in: ObservationCreate, db: Session = Depends(get_db)):
    """
    Submit a patient observation and store it in PostgreSQL.
    Accepts either patient_id or patient_code.
    """
    patient_id = obs_in.patient_id

    if not patient_id:
        if not obs_in.patient_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'patient_id' or 'patient_code' must be provided."
            )
        patient = db.query(Patient).filter(Patient.patient_code == obs_in.patient_code.strip()).first()
        if not patient:
            # Auto-create patient record for smooth simulation if unknown
            patient = Patient(
                patient_code=obs_in.patient_code.strip(),
                name=f"Simulated {obs_in.patient_code.strip()}",
                age=45,
                surgery_type="General Post-Operative Recovery",
                surgery_date=datetime.utcnow().date()
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
        patient_id = patient.id
    else:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {patient_id} does not exist."
            )

    # Temperature normalization
    temp_val = obs_in.temperature
    if obs_in.sensor_status.strip().capitalize() == "Missing":
        temp_val = None

    observation = Observation(
        patient_id=patient_id,
        temperature=temp_val,
        pain_score=obs_in.pain_score,
        wound_status=obs_in.wound_status.strip().capitalize(),
        symptom_description=obs_in.symptom_description,
        sensor_status=obs_in.sensor_status.strip().capitalize(),
        timestamp=datetime.utcnow()
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


@app.get("/patients/{patient_id}/observations", response_model=List[ObservationRead], tags=["Observations"])
def get_patient_observations(patient_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all observation entries recorded for a given patient.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} was not found."
        )
    return db.query(Observation).filter(Observation.patient_id == patient_id).order_by(Observation.timestamp.desc()).all()


# ----------------------------------------------------------------------
# 4. Rule-Based Risk Assessment Endpoints
# ----------------------------------------------------------------------
@app.post("/assess/{observation_id}", response_model=AssessmentResult, tags=["Assessment"])
def assess_observation(observation_id: int, db: Session = Depends(get_db)):
    """
    Execute the EXISTING rule-based risk assessment engine on an observation.
    Returns:
    - risk_level (LOW, MEDIUM, HIGH, CONFLICT)
    - reason (transparent explanation)
    - recommendation (actionable guidance)
    
    If risk is HIGH or CONFLICT, automatically ensures an Escalation record is created.
    """
    observation = db.query(Observation).filter(Observation.id == observation_id).first()
    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with ID {observation_id} was not found."
        )

    # Call existing rule-based engine
    result = evaluate_observation(
        temperature=observation.temperature,
        pain_score=observation.pain_score,
        wound_status=observation.wound_status,
        symptom_description=observation.symptom_description,
        sensor_status=observation.sensor_status
    )

    escalation_id = None
    # If assessed as HIGH or CONFLICT, create or update escalation record
    if result["risk_level"] in ["HIGH", "CONFLICT"]:
        existing_esc = db.query(Escalation).filter(Escalation.observation_id == observation.id).first()
        if not existing_esc:
            esc = Escalation(
                patient_id=observation.patient_id,
                observation_id=observation.id,
                risk_level=result["risk_level"],
                reason=result["reason"],
                recommendation=result["recommendation"],
                status="OPEN"
            )
            db.add(esc)
            db.commit()
            db.refresh(esc)
            escalation_id = esc.id
        else:
            escalation_id = existing_esc.id

    return AssessmentResult(
        risk_level=result["risk_level"],
        reason=result["reason"],
        recommendation=result["recommendation"],
        observation_id=observation.id,
        escalation_id=escalation_id
    )


@app.get("/assessments", response_model=List[ObservationAssessmentDetail], tags=["Assessment"])
def list_assessments(
    risk_level: Optional[str] = Query(None, description="Filter by risk level: LOW, MEDIUM, HIGH, CONFLICT"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    View assessment results joined with observation vitals, patient code, and escalation status.
    Used directly by the Clinician Dashboard.
    """
    query = (
        db.query(Observation, Patient, Escalation)
        .join(Patient, Observation.patient_id == Patient.id)
        .outerjoin(Escalation, Observation.id == Escalation.observation_id)
        .order_by(Observation.timestamp.desc())
    )

    results = query.limit(limit).all()

    assessment_details = []
    target_risk = risk_level.strip().upper() if risk_level else None

    for obs, patient, esc in results:
        eval_res = evaluate_observation(
            temperature=obs.temperature,
            pain_score=obs.pain_score,
            wound_status=obs.wound_status,
            symptom_description=obs.symptom_description,
            sensor_status=obs.sensor_status
        )

        if target_risk and eval_res["risk_level"] != target_risk:
            continue

        assessment_details.append(
            ObservationAssessmentDetail(
                observation_id=obs.id,
                patient_id=patient.id,
                patient_code=patient.patient_code,
                temperature=obs.temperature,
                pain_score=obs.pain_score,
                wound_status=obs.wound_status,
                symptom_description=obs.symptom_description,
                sensor_status=obs.sensor_status,
                timestamp=obs.timestamp,
                risk_level=eval_res["risk_level"],
                reason=eval_res["reason"],
                recommendation=eval_res["recommendation"],
                escalation_status=esc.status if esc else None,
                escalation_id=esc.id if esc else None,
                assigned_staff=esc.assigned_staff if esc else None,
                due_date=esc.due_date if esc else None
            )
        )

    return assessment_details


# ----------------------------------------------------------------------
# 5. Escalation & Follow-Up Tracking Endpoints (Phase 8)
# ----------------------------------------------------------------------
@app.post("/escalations", response_model=EscalationRead, status_code=status.HTTP_201_CREATED, tags=["Escalations"])
def create_escalation(esc_in: EscalationCreate, db: Session = Depends(get_db)):
    """
    Manually or programmatically create an escalation record.
    """
    # Verify observation exists
    obs = db.query(Observation).filter(Observation.id == esc_in.observation_id).first()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation ID {esc_in.observation_id} does not exist."
        )

    existing = db.query(Escalation).filter(Escalation.observation_id == esc_in.observation_id).first()
    if existing:
        return existing

    esc = Escalation(
        patient_id=esc_in.patient_id,
        observation_id=esc_in.observation_id,
        risk_level=esc_in.risk_level.upper(),
        reason=esc_in.reason,
        recommendation=esc_in.recommendation,
        status=esc_in.status.upper() if esc_in.status else "OPEN",
        assigned_staff=esc_in.assigned_staff,
        due_date=esc_in.due_date
    )
    db.add(esc)
    db.commit()
    db.refresh(esc)
    return esc


@app.get("/escalations", response_model=List[EscalationRead], tags=["Escalations"])
def get_escalations(
    status: Optional[str] = Query(None, description="Filter by status: OPEN, IN_PROGRESS, RESOLVED"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: HIGH, CONFLICT"),
    db: Session = Depends(get_db)
):
    """
    View escalation cases, with optional filtering by status and risk level.
    """
    query = db.query(Escalation).join(Patient, Escalation.patient_id == Patient.id)
    if status:
        query = query.filter(Escalation.status == status.strip().upper())
    if risk_level:
        query = query.filter(Escalation.risk_level == risk_level.strip().upper())

    escalations = query.order_by(Escalation.created_at.desc()).all()
    results = []
    for esc in escalations:
        esc_dict = {
            "id": esc.id,
            "patient_id": esc.patient_id,
            "observation_id": esc.observation_id,
            "patient_code": esc.patient.patient_code if esc.patient else None,
            "risk_level": esc.risk_level,
            "reason": esc.reason,
            "recommendation": esc.recommendation,
            "status": esc.status,
            "assigned_staff": esc.assigned_staff,
            "due_date": esc.due_date,
            "created_at": esc.created_at,
            "updated_at": esc.updated_at
        }
        results.append(EscalationRead(**esc_dict))
    return results


@app.get("/escalations/{escalation_id}", response_model=EscalationRead, tags=["Escalations"])
def get_escalation(escalation_id: int, db: Session = Depends(get_db)):
    """
    View details for a specific escalation record.
    """
    esc = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Escalation with ID {escalation_id} was not found."
        )
    return EscalationRead(
        id=esc.id,
        patient_id=esc.patient_id,
        observation_id=esc.observation_id,
        patient_code=esc.patient.patient_code if esc.patient else None,
        risk_level=esc.risk_level,
        reason=esc.reason,
        recommendation=esc.recommendation,
        status=esc.status,
        assigned_staff=esc.assigned_staff,
        due_date=esc.due_date,
        created_at=esc.created_at,
        updated_at=esc.updated_at
    )


@app.patch("/escalations/{escalation_id}/status", response_model=EscalationRead, tags=["Escalations"])
def update_escalation_status(
    escalation_id: int,
    payload: EscalationStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update escalation workflow status: OPEN -> IN_PROGRESS -> RESOLVED.
    """
    esc = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Escalation with ID {escalation_id} was not found."
        )
    esc.status = payload.status
    esc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(esc)
    return EscalationRead(
        id=esc.id,
        patient_id=esc.patient_id,
        observation_id=esc.observation_id,
        patient_code=esc.patient.patient_code if esc.patient else None,
        risk_level=esc.risk_level,
        reason=esc.reason,
        recommendation=esc.recommendation,
        status=esc.status,
        assigned_staff=esc.assigned_staff,
        due_date=esc.due_date,
        created_at=esc.created_at,
        updated_at=esc.updated_at
    )


@app.patch("/escalations/{escalation_id}/assign", response_model=EscalationRead, tags=["Escalations"])
def assign_escalation(
    escalation_id: int,
    payload: EscalationAssignUpdate,
    db: Session = Depends(get_db)
):
    """
    Assign a clinician or authorized staff member to the escalation case.
    """
    esc = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Escalation with ID {escalation_id} was not found."
        )
    esc.assigned_staff = payload.assigned_staff.strip()
    if esc.status == "OPEN":
        esc.status = "IN_PROGRESS"
    esc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(esc)
    return EscalationRead(
        id=esc.id,
        patient_id=esc.patient_id,
        observation_id=esc.observation_id,
        patient_code=esc.patient.patient_code if esc.patient else None,
        risk_level=esc.risk_level,
        reason=esc.reason,
        recommendation=esc.recommendation,
        status=esc.status,
        assigned_staff=esc.assigned_staff,
        due_date=esc.due_date,
        created_at=esc.created_at,
        updated_at=esc.updated_at
    )


@app.patch("/escalations/{escalation_id}/due-date", response_model=EscalationRead, tags=["Escalations"])
def update_escalation_due_date(
    escalation_id: int,
    payload: EscalationDueDateUpdate,
    db: Session = Depends(get_db)
):
    """
    Set or update the target follow-up completion due date.
    """
    esc = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Escalation with ID {escalation_id} was not found."
        )
    esc.due_date = payload.due_date
    esc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(esc)
    return EscalationRead(
        id=esc.id,
        patient_id=esc.patient_id,
        observation_id=esc.observation_id,
        patient_code=esc.patient.patient_code if esc.patient else None,
        risk_level=esc.risk_level,
        reason=esc.reason,
        recommendation=esc.recommendation,
        status=esc.status,
        assigned_staff=esc.assigned_staff,
        due_date=esc.due_date,
        created_at=esc.created_at,
        updated_at=esc.updated_at
    )


# ----------------------------------------------------------------------
# 6. Web Page Routes
# ----------------------------------------------------------------------
@app.get("/patient", tags=["Web Interface"])
def serve_patient_interface():
    """Serve the Patient Web Reporting Interface."""
    filepath = os.path.join(FRONTEND_DIR, "patient.html")
    if os.path.exists(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404, detail="Patient interface template not found")


@app.get("/clinician", tags=["Web Interface"])
def serve_clinician_dashboard():
    """Serve the Clinician Decision Support Dashboard."""
    filepath = os.path.join(FRONTEND_DIR, "clinician.html")
    if os.path.exists(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404, detail="Clinician dashboard template not found")
