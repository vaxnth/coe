"""
Comprehensive Automated Test Suite for 70% Milestone:
Phases 5 through 8 (FastAPI, Rules, Escalations, Follow-up Tracking, DB Persistence)
"""
import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import Patient, Observation, Escalation


client = TestClient(app)


def test_1_root_and_health():
    """Verify FastAPI starts, GET / works, and GET /health confirms PostgreSQL connectivity."""
    # 1. Root
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["project_completion"] == "70%"
    assert "safety_disclaimer" in data

    # 2. Health check with PostgreSQL
    h_res = client.get("/health")
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert h_data["status"] == "healthy"
    assert h_data["database"] == "connected"


def test_2_patient_creation_and_retrieval():
    """Verify simulated patient creation (POST /patients) and retrieval."""
    unique_code = f"TEST-{datetime.utcnow().strftime('%H%M%S%f')}"
    payload = {
        "patient_code": unique_code,
        "name": "Integration Test Patient",
        "age": 52,
        "surgery_type": "Laparoscopic Appendectomy",
        "surgery_date": str(date.today() - timedelta(days=2))
    }
    create_res = client.post("/patients", json=payload)
    assert create_res.status_code == 201
    created_patient = create_res.json()
    assert created_patient["patient_code"] == unique_code
    patient_id = created_patient["id"]

    # Retrieve patient
    get_res = client.get(f"/patients/{patient_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Integration Test Patient"


def test_3_low_risk_observation_and_assessment():
    """Verify LOW risk observation submission and assessment."""
    obs_res = client.post("/observations", json={
        "patient_code": "PAT-001",
        "temperature": 36.8,
        "pain_score": 2,
        "wound_status": "Normal",
        "symptom_description": "Resting comfortably, surgical site clean",
        "sensor_status": "Normal"
    })
    assert obs_res.status_code == 201
    obs_data = obs_res.json()
    obs_id = obs_data["id"]

    assess_res = client.post(f"/assess/{obs_id}")
    assert assess_res.status_code == 200
    assessment = assess_res.json()
    assert assessment["risk_level"] == "LOW"
    assert "expected recovery baseline" in assessment["reason"]
    # LOW risk should NOT create an escalation
    assert assessment["escalation_id"] is None


def test_4_medium_risk_observation():
    """Verify MEDIUM risk observation evaluation."""
    obs_res = client.post("/observations", json={
        "patient_code": "PAT-001",
        "temperature": 37.9,
        "pain_score": 5,
        "wound_status": "Redness",
        "symptom_description": "Incision feels warm to touch, moderate throbbing",
        "sensor_status": "Normal"
    })
    assert obs_res.status_code == 201
    obs_id = obs_res.json()["id"]

    assess_res = client.post(f"/assess/{obs_id}")
    assert assess_res.status_code == 200
    assessment = assess_res.json()
    assert assessment["risk_level"] == "MEDIUM"
    assert "Follow-up recommended" in assessment["recommendation"]


def test_5_high_risk_and_automatic_escalation():
    """Verify HIGH risk observation, rule assessment, and auto-creation of escalation."""
    obs_res = client.post("/observations", json={
        "patient_code": "PAT-002",
        "temperature": 39.4,
        "pain_score": 9,
        "wound_status": "Discharge",
        "symptom_description": "Severe pain unresponsive to analgesics, purulent drainage noted",
        "sensor_status": "Normal"
    })
    assert obs_res.status_code == 201
    obs_id = obs_res.json()["id"]

    assess_res = client.post(f"/assess/{obs_id}")
    assert assess_res.status_code == 200
    assessment = assess_res.json()
    assert assessment["risk_level"] == "HIGH"
    assert assessment["escalation_id"] is not None

    # Check that escalation is registered in GET /escalations
    esc_res = client.get(f"/escalations/{assessment['escalation_id']}")
    assert esc_res.status_code == 200
    esc = esc_res.json()
    assert esc["risk_level"] == "HIGH"
    assert esc["status"] == "OPEN"


def test_6_conflict_detection_and_escalation():
    """Verify CONFLICT observation where normal sensor conflicts with fever/chills symptoms."""
    obs_res = client.post("/observations", json={
        "patient_code": "PAT-003",
        "temperature": 36.6,
        "pain_score": 4,
        "wound_status": "Normal",
        "symptom_description": "Patient complaints of severe chills, shaking fever and sweating",
        "sensor_status": "Normal"
    })
    assert obs_res.status_code == 201
    obs_id = obs_res.json()["id"]

    assess_res = client.post(f"/assess/{obs_id}")
    assert assess_res.status_code == 200
    assessment = assess_res.json()
    assert assessment["risk_level"] == "CONFLICT"
    assert "Conflict detected" in assessment["reason"]
    assert assessment["escalation_id"] is not None


def test_7_missing_and_noisy_sensor_handling():
    """Verify system handles Missing (null temp) and Noisy sensor flags gracefully."""
    # 1. Missing sensor
    missing_res = client.post("/observations", json={
        "patient_code": "PAT-004",
        "temperature": None,
        "pain_score": 3,
        "wound_status": "Normal",
        "symptom_description": "Sensor detached during sleep",
        "sensor_status": "Missing"
    })
    assert missing_res.status_code == 201
    missing_id = missing_res.json()["id"]
    m_assess = client.post(f"/assess/{missing_id}").json()
    assert "Data quality limitation" in m_assess["reason"]

    # 2. Noisy sensor
    noisy_res = client.post("/observations", json={
        "patient_code": "PAT-004",
        "temperature": 45.2,  # Unphysiological reading
        "pain_score": 2,
        "wound_status": "Normal",
        "symptom_description": "Erratic telemetry jumps logged",
        "sensor_status": "Noisy"
    })
    assert noisy_res.status_code == 201
    noisy_id = noisy_res.json()["id"]
    n_assess = client.post(f"/assess/{noisy_id}").json()
    assert "noisy/unreliable" in n_assess["reason"]


def test_8_phase_8_escalation_lifecycle_and_followup():
    """
    Verify complete follow-up workflow:
    1. Create/Identify escalation
    2. Assign to clinician
    3. Set target due date
    4. Transition status: OPEN -> IN_PROGRESS -> RESOLVED
    5. Verify PostgreSQL persistence
    """
    # Create high risk observation
    obs_res = client.post("/observations", json={
        "patient_code": "PAT-005",
        "temperature": 39.1,
        "pain_score": 8,
        "wound_status": "Bleeding",
        "symptom_description": "Active bleeding around incision site",
        "sensor_status": "Normal"
    })
    obs_id = obs_res.json()["id"]
    assess_data = client.post(f"/assess/{obs_id}").json()
    esc_id = assess_data["escalation_id"]
    assert esc_id is not None

    # Verify initial status is OPEN
    esc = client.get(f"/escalations/{esc_id}").json()
    assert esc["status"] == "OPEN"
    assert esc["assigned_staff"] is None

    # Step 2: Assign clinician
    assign_res = client.patch(f"/escalations/{esc_id}/assign", json={
        "assigned_staff": "Dr. Sarah Miller, MD"
    })
    assert assign_res.status_code == 200
    assigned_esc = assign_res.json()
    assert assigned_esc["assigned_staff"] == "Dr. Sarah Miller, MD"
    assert assigned_esc["status"] == "IN_PROGRESS"

    # Step 3: Set Due Date
    target_due = (datetime.utcnow() + timedelta(hours=4)).isoformat()
    due_res = client.patch(f"/escalations/{esc_id}/due-date", json={
        "due_date": target_due
    })
    assert due_res.status_code == 200
    assert due_res.json()["due_date"] is not None

    # Step 4: Transition to RESOLVED
    status_res = client.patch(f"/escalations/{esc_id}/status", json={
        "status": "RESOLVED"
    })
    assert status_res.status_code == 200
    resolved_esc = status_res.json()
    assert resolved_esc["status"] == "RESOLVED"

    # Step 5: Verify directly in PostgreSQL via SessionLocal
    db = SessionLocal()
    try:
        db_esc = db.query(Escalation).filter(Escalation.id == esc_id).first()
        assert db_esc is not None
        assert db_esc.status == "RESOLVED"
        assert db_esc.assigned_staff == "Dr. Sarah Miller, MD"
        assert db_esc.due_date is not None
    finally:
        db.close()


def test_9_assessments_endpoint_for_dashboard():
    """Verify GET /assessments returns populated dataset for the Clinician Dashboard."""
    res = client.get("/assessments?limit=20")
    assert res.status_code == 200
    items = res.json()
    assert len(items) > 0
    first = items[0]
    assert "patient_code" in first
    assert "risk_level" in first
    assert "reason" in first
    assert "recommendation" in first


def test_10_web_interface_endpoints():
    """Verify web HTML templates are served cleanly."""
    res_pat = client.get("/patient")
    assert res_pat.status_code == 200
    assert "Post-Operative Self-Reporting Portal" in res_pat.text

    res_clin = client.get("/clinician")
    assert res_clin.status_code == 200
    assert "Clinician Decision Support Dashboard" in res_clin.text
