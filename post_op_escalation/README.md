# Post-Operative Escalation Prototype (70% Milestone)

**Project Title:** A Field-Ready Prototype for Post-Operative Patients Reporting Pain, Temperature & Wound Observations  
**Current Milestone:** Strict 70% Implementation (Phases 1 through 8 Completed)  
**Target Completion:** 70% (Development stopped strictly before the final 30%)  
**Academic Prototype Notice:** This software is an academic research decision-support prototype intended solely for simulated post-operative monitoring analysis. It does NOT provide clinical diagnoses or autonomous medical decisions. Final decisions remain with clinicians or authorized staff.

---

## 1. Overview of Implemented Scope (70%)

This repository contains the complete 70% milestone across eight fully operational phases:

- **Phase 1 — Project Foundation:** Architecture setup, virtual environment, and dependency management.
- **Phase 2 — Database Layer:** PostgreSQL configuration with SQLAlchemy ORM models (`Patient`, `Observation`, `Escalation`) and Pydantic v2 schemas.
- **Phase 3 — Simulated Data Generation:** Pipeline (`data/generate_data.py`) synthesizing 155 post-operative observation records covering all 6 clinical scenarios.
- **Phase 4 — Rule-Based Risk & Conflict Engine:** Transparent, deterministic engine (`backend/rules.py`) categorizing observations into `LOW`, `MEDIUM`, `HIGH`, or `CONFLICT`.
- **Phase 5 — FastAPI Backend & REST APIs:** Complete REST API (`backend/main.py`) with PostgreSQL connectivity, Pydantic validation, and comprehensive clinical endpoints.
- **Phase 6 — Patient Web Interface:** Clean HTML/CSS/Vanilla JS portal (`/patient`) for patient self-reporting with instant rule-based evaluation feedback and decision-support notices.
- **Phase 7 — Clinician Dashboard:** Live decision-support dashboard (`/clinician`) retrieving real PostgreSQL data, displaying summary metrics, risk filters, and high-visibility urgency badges.
- **Phase 8 — Escalation & Follow-Up Tracking:** Complete escalation lifecycle management (`OPEN` &rarr; `IN_PROGRESS` &rarr; `RESOLVED`), clinician assignment, and due-date tracking.

---

## 2. Directory Structure

```
post_op_escalation/
│
├── backend/
│   ├── database.py       # PostgreSQL connection, session management, table creation
│   ├── models.py         # SQLAlchemy ORM models (Patient, Observation, Escalation)
│   ├── schemas.py        # Pydantic v2 validation schemas
│   ├── rules.py          # Deterministic rule-based risk & conflict assessment engine
│   ├── main.py           # FastAPI REST application & web route handlers
│   ├── seed_data.py      # Database seeder populating PostgreSQL with simulated cases
│   └── tests/
│       └── test_workflow.py # Comprehensive automated test suite (10 test suites)
│
├── frontend/
│   ├── patient.html      # Patient self-reporting web interface
│   ├── clinician.html    # Clinician decision support dashboard
│   ├── css/
│   │   └── styles.css    # Unified clinical UI design system
│   └── js/
│       ├── patient.js    # Patient portal frontend logic & API communication
│       └── clinician.js  # Clinician dashboard metrics, filtering & follow-up tracking
│
├── data/
│   ├── generate_data.py  # Synthetic dataset generator for 6 clinical scenarios
│   └── simulated_observations.csv # Generated dataset (155 records)
│
├── .env                  # Active PostgreSQL configuration
├── .env.example          # Environment variables template
├── requirements.txt      # Core project dependencies
├── .gitignore            # Python environment ignore rules
└── README.md             # 70% milestone documentation
```

---

## 3. Database Schema

1. **`patients` Table:**
   - `id` (Integer, Primary Key)
   - `patient_code` (String, Unique, Indexed)
   - `name` (String)
   - `age` (Integer)
   - `surgery_type` (String)
   - `surgery_date` (Date)
   - `created_at` (DateTime)
   - Relationships: `observations` (one-to-many), `escalations` (one-to-many)

2. **`observations` Table:**
   - `id` (Integer, Primary Key)
   - `patient_id` (Integer, Foreign Key to `patients.id`)
   - `temperature` (Float, Nullable for missing sensor)
   - `pain_score` (Integer, 0–10)
   - `wound_status` (String: `Normal`, `Redness`, `Swelling`, `Discharge`, `Bleeding`, `Unknown`)
   - `symptom_description` (Text, Nullable)
   - `sensor_status` (String: `Normal`, `Noisy`, `Missing`)
   - `timestamp` (DateTime)
   - Relationships: `patient` (many-to-one), `escalation` (one-to-one)

3. **`escalations` Table (Phase 8 Enhanced):**
   - `id` (Integer, Primary Key)
   - `patient_id` (Integer, Foreign Key to `patients.id`)
   - `observation_id` (Integer, Foreign Key to `observations.id`)
   - `risk_level` (String: `HIGH`, `CONFLICT`)
   - `reason` (Text, transparent clinical explanation)
   - `recommendation` (Text, actionable triage advice)
   - `status` (String: `OPEN`, `IN_PROGRESS`, `RESOLVED`)
   - `assigned_staff` (String, Nullable, assigned clinician/staff name)
   - `due_date` (DateTime, Nullable, target follow-up completion deadline)
   - `created_at` (DateTime)
   - `updated_at` (DateTime)
   - Relationships: `patient` (many-to-one), `observation` (one-to-one)

---

## 4. FastAPI REST API Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Application status, milestone metadata, and safety notice |
| `GET` | `/health` | Backend and PostgreSQL connectivity health check |
| `POST` | `/patients` | Create a simulated patient |
| `GET` | `/patients` | Retrieve list of simulated patients |
| `GET` | `/patients/{patient_id}` | Retrieve details of a single patient |
| `POST` | `/observations` | Submit a patient observation into PostgreSQL |
| `GET` | `/patients/{patient_id}/observations` | Retrieve observations for a given patient |
| `POST` | `/assess/{observation_id}` | Run deterministic rule engine on observation (auto-creates escalation if HIGH/CONFLICT) |
| `GET` | `/assessments` | Retrieve observation assessments for clinician dashboard |
| `POST` | `/escalations` | Create a clinical escalation record |
| `GET` | `/escalations` | View escalation cases (supports status/risk filtering) |
| `GET` | `/escalations/{escalation_id}` | View details of a specific escalation |
| `PATCH` | `/escalations/{escalation_id}/status` | Update status (`OPEN` &rarr; `IN_PROGRESS` &rarr; `RESOLVED`) |
| `PATCH` | `/escalations/{escalation_id}/assign` | Assign case to clinician / authorized staff member |
| `PATCH` | `/escalations/{escalation_id}/due-date` | Set or update follow-up deadline |
| `GET` | `/patient` | Serve patient self-reporting web interface |
| `GET` | `/clinician` | Serve clinician decision support dashboard |

---

## 5. End-to-End Workflow Verification

```
Patient Web Form (/patient)
        ↓ (POST /observations)
FastAPI Backend
        ↓ (SQLAlchemy ORM)
PostgreSQL Database
        ↓ (POST /assess/{id})
Rule-Based Risk Engine (backend/rules.py)
        ↓
Risk Assessment (HIGH / CONFLICT)
        ↓
Escalation Created (Status: OPEN)
        ↓
Clinician Dashboard (/clinician)
        ↓ (PATCH /escalations/{id}/assign)
Assigned to Clinician (Status: IN_PROGRESS)
        ↓ (PATCH /escalations/{id}/due-date)
Follow-Up Due Date Set
        ↓ (PATCH /escalations/{id}/status)
Follow-Up Completed (Status: RESOLVED)
```

---

## 6. How to Run & Verify

1. **Activate Virtual Environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Seed the Database with Simulated Data:**
   ```bash
   python -m backend.seed_data
   ```

3. **Run Automated Test Suite:**
   ```bash
   python -m pytest backend/tests/test_workflow.py -v
   ```

4. **Start the FastAPI Web Server:**
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. **Access the Interfaces:**
   - **Patient Reporting Portal:** [http://127.0.0.1:8000/patient](http://127.0.0.1:8000/patient)
   - **Clinician Dashboard:** [http://127.0.0.1:8000/clinician](http://127.0.0.1:8000/clinician)
   - **Interactive API Documentation (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
