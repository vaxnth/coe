import os
import pandas as pd
from datetime import datetime, date, timedelta
import random

from .database import SessionLocal, create_tables
from .models import Patient, Observation, Escalation
from .rules import evaluate_observation


SURGERY_TYPES = [
    "Laparoscopic Cholecystectomy",
    "Appendectomy",
    "Total Knee Arthroplasty",
    "Inguinal Hernia Repair",
    "Open Lumbar Spine Decompression",
    "Total Hip Arthroplasty",
    "Bowel Resection"
]

STAFF_MEMBERS = [
    "Dr. S. Miller, MD",
    "Nurse R. Chen, BSN",
    "Charge Nurse K. Patel, RN",
    "Dr. A. Taylor, MD",
    "Nurse J. Washington, RN"
]


def seed_database(force_refresh: bool = False):
    """
    Seed PostgreSQL with simulated post-operative patients, observations,
    and rule-based assessments/escalations.
    """
    create_tables()
    db = SessionLocal()

    try:
        existing_patient_count = db.query(Patient).count()
        if existing_patient_count > 0 and not force_refresh:
            print(f"Database already populated ({existing_patient_count} patients). Skipping seed.")
            return

        if force_refresh:
            print("Clearing existing data...")
            db.query(Escalation).delete()
            db.query(Observation).delete()
            db.query(Patient).delete()
            db.commit()

        print("Seeding simulated post-operative patients (PAT-001 to PAT-035)...")
        patient_map = {}
        today = date.today()

        first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
                       "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
                       "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
                       "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
                       "Steven", "Kimberly", "Paul"]

        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                      "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
                      "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
                      "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
                      "Young", "Allen", "King", "Wright"]

        for i in range(1, 36):
            p_code = f"PAT-{i:03d}"
            p_name = f"{first_names[(i - 1) % len(first_names)]} {last_names[(i - 1) % len(last_names)]}"
            surgery = SURGERY_TYPES[i % len(SURGERY_TYPES)]
            s_date = today - timedelta(days=random.randint(1, 7))
            age = random.randint(28, 78)

            patient = Patient(
                patient_code=p_code,
                name=p_name,
                age=age,
                surgery_type=surgery,
                surgery_date=s_date,
                created_at=datetime.utcnow() - timedelta(days=random.randint(2, 10))
            )
            db.add(patient)
            db.flush()
            patient_map[p_code] = patient.id

        # Load simulated observations from CSV
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "simulated_observations.csv"
        )

        if not os.path.exists(csv_path):
            print(f"Warning: {csv_path} not found. Skipping observation seeding.")
            db.commit()
            return

        df = pd.read_csv(csv_path)
        print(f"Loading {len(df)} synthetic observations from {csv_path}...")

        base_time = datetime.utcnow() - timedelta(days=3)
        escalation_count = 0

        for idx, row in df.iterrows():
            p_code = str(row["patient_code"]).strip()
            if p_code not in patient_map:
                continue

            temp_val = float(row["temperature"]) if pd.notna(row["temperature"]) else None
            pain_val = int(row["pain_score"])
            wound_val = str(row["wound_status"]).strip()
            symptom_val = str(row["symptom_description"]).strip() if pd.notna(row["symptom_description"]) else None
            sensor_val = str(row["sensor_status"]).strip()
            obs_time = base_time + timedelta(minutes=idx * 25)

            obs = Observation(
                patient_id=patient_map[p_code],
                temperature=temp_val,
                pain_score=pain_val,
                wound_status=wound_val,
                symptom_description=symptom_val,
                sensor_status=sensor_val,
                timestamp=obs_time
            )
            db.add(obs)
            db.flush()

            # Evaluate with existing rule engine
            assessment = evaluate_observation(
                temperature=temp_val,
                pain_score=pain_val,
                wound_status=wound_val,
                symptom_description=symptom_val,
                sensor_status=sensor_val
            )

            # High or Conflict creates an escalation
            if assessment["risk_level"] in ["HIGH", "CONFLICT"]:
                # Seed diverse statuses for realistic demonstration: OPEN, IN_PROGRESS, RESOLVED
                status_choices = ["OPEN", "OPEN", "IN_PROGRESS", "RESOLVED"]
                chosen_status = random.choice(status_choices)

                assigned = None
                due = None
                if chosen_status in ["IN_PROGRESS", "RESOLVED"]:
                    assigned = random.choice(STAFF_MEMBERS)
                    due = obs_time + timedelta(hours=random.randint(2, 12))

                escalation = Escalation(
                    patient_id=patient_map[p_code],
                    observation_id=obs.id,
                    risk_level=assessment["risk_level"],
                    reason=assessment["reason"],
                    recommendation=assessment["recommendation"],
                    status=chosen_status,
                    assigned_staff=assigned,
                    due_date=due,
                    created_at=obs_time,
                    updated_at=obs_time + timedelta(minutes=random.randint(5, 30))
                )
                db.add(escalation)
                escalation_count += 1

        db.commit()
        total_obs = db.query(Observation).count()
        total_esc = db.query(Escalation).count()
        print(f"Seeding completed successfully: {len(patient_map)} patients, {total_obs} observations, {total_esc} escalations.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database(force_refresh=True)
