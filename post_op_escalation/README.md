# Post-Operative Escalation Prototype (35% Milestone)

**Project Title:** A Field-Ready Prototype for Post-Operative Patients Reporting Pain, Temperature and Wound Observations  
**Milestone:** Strict 35% Implementation (Phases 1–4)  
**Academic Prototype Notice:** This software is an academic research prototype intended solely for simulated post-operative monitoring analysis. It does NOT provide clinical diagnoses or autonomous medical decisions.

---

## 1. Overview of Implemented Scope (35%)

This repository contains the completed foundation, database architecture, simulated observation data generator, and transparent rule-based risk/conflict assessment engine:

- **Phase 1 — Project Foundation:** Directory structure, dependency specifications (`requirements.txt`), environment variable template (`.env.example`), and project guidelines.
- **Phase 2 — Database Layer:** PostgreSQL configuration with SQLAlchemy ORM models (`Patient`, `Observation`, `Escalation`) and strict relationship cascades, accompanied by Pydantic v2 schemas for robust serialization.
- **Phase 3 — Simulated Data Generation:** Generation pipeline (`data/generate_data.py`) synthesizing 155 post-operative observation records covering all 6 required clinical scenarios.
- **Phase 4 — Rule-Based Risk and Conflict Engine:** Deterministic, fully explainable rule-based logic (`backend/rules.py`) categorizing observations into `LOW`, `MEDIUM`, `HIGH`, or `CONFLICT`, with data-quality handling for noisy/missing telemetry.

*(Phases 5 through 8 — including FastAPI endpoints, web frontend, clinician dashboard, alerting integrations, and deployment — are intentionally excluded from this milestone).*

---

## 2. Directory Structure

```
post_op_escalation/
│
├── backend/
│   ├── database.py       # PostgreSQL database connection and session management
│   ├── models.py         # SQLAlchemy ORM models (Patient, Observation, Escalation)
│   ├── schemas.py        # Pydantic data validation schemas
│   └── rules.py          # Explainable rule-based risk and conflict engine
│
├── data/
│   ├── generate_data.py  # Synthetic dataset generator for 6 clinical scenarios
│   └── simulated_observations.csv # Generated dataset (155 records)
│
├── .env.example          # Environment variables template
├── requirements.txt      # Core project dependencies
├── .gitignore            # Python environment ignore rules
└── README.md             # Milestone documentation
```

---

## 3. Database Schema

The database is built on SQLAlchemy with PostgreSQL compatibility:

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

3. **`escalations` Table:**
   - `id` (Integer, Primary Key)
   - `patient_id` (Integer, Foreign Key to `patients.id`)
   - `observation_id` (Integer, Foreign Key to `observations.id`)
   - `risk_level` (String: `LOW`, `MEDIUM`, `HIGH`, `CONFLICT`)
   - `reason` (Text, transparent explanation)
   - `recommendation` (Text, non-diagnostic guidance)
   - `created_at` (DateTime)
   - Relationships: `patient` (many-to-one), `observation` (one-to-one)

---

## 4. Simulated Dataset

Generated using `python data/generate_data.py`, output to `data/simulated_observations.csv`.

**Columns:**
`patient_code`, `temperature`, `pain_score`, `wound_status`, `symptom_description`, `sensor_status`

**Clinical Scenarios Covered:**
1. **Normal Observations:** Stable baseline vitals (temp 36.3–37.2°C, pain 0–3, wound Normal).
2. **Medium-Risk Observations:** Moderate pain (4–6) or moderate fever (37.5–38.4°C) or minor wound issues (`Redness`, `Swelling`).
3. **High-Risk Observations:** Severe pain (7–10) or high fever (≥38.5°C) or acute wound complications (`Discharge`, `Bleeding`).
4. **Conflicting Observations:** Sensor reads normal body temperature (36.4–37.1°C), but patient reports chills, rigors, or severe fever sensation.
5. **Missing Sensor Data:** Telemetry uncoupled or missing (`temperature` is null, `sensor_status` = `Missing`).
6. **Noisy Sensor Data:** Hardware artifacts or erratic sensor values (`sensor_status` = `Noisy`).

---

## 5. Rule-Based Risk & Conflict Assessment

The engine in `backend/rules.py` implements pure deterministic rules without black-box ML:

- **Input:** `temperature`, `pain_score`, `wound_status`, `symptom_description`, `sensor_status`
- **Output:**
  ```json
  {
    "risk_level": "HIGH",
    "reason": "Severely abnormal temperature recorded (39.1°C). Severe pain level reported (8/10). Critical wound observation noted (Discharge).",
    "recommendation": "Clinician review is required. Prompt clinical evaluation and physical assessment recommended."
  }
  ```

---

## 6. How to Run & Verify

1. **Create and activate environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Update DATABASE_URL with your PostgreSQL credentials
   ```

3. **Generate synthetic dataset:**
   ```bash
   python data/generate_data.py
   ```

4. **Verify rules and models:**
   ```bash
   python -c "from backend.models import Base; print('Models valid. Registered tables:', list(Base.metadata.tables.keys()))"
   ```
