import os
import random
import pandas as pd
import numpy as np

# Seed for deterministic and reproducible academic simulation
random.seed(42)
np.random.seed(42)

WOUND_STATUSES = ["Normal", "Redness", "Swelling", "Discharge", "Bleeding", "Unknown"]
SENSOR_STATUSES = ["Normal", "Noisy", "Missing"]


def generate_simulated_dataset(total_records: int = 150) -> pd.DataFrame:
    """
    Generate synthetic post-operative patient observations across 6 distinct categories:
    1. Normal observations
    2. Medium-risk observations
    3. High-risk observations
    4. Conflicting observations
    5. Missing sensor data
    6. Noisy sensor data
    """
    records = []
    patient_pool = [f"PAT-{i:03d}" for i in range(1, 36)]

    # 1. Normal observations (~30 records)
    normal_symptoms = [
        "Patient resting comfortably, no acute distress",
        "Mild surgical site soreness, expected post-op",
        "Walking around room with minimal discomfort",
        "Dressing clean and intact, pain well-managed",
        "Tolerating oral intake, sleeping well"
    ]
    for _ in range(30):
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": round(random.uniform(36.3, 37.2), 1),
            "pain_score": random.randint(0, 3),
            "wound_status": "Normal",
            "symptom_description": random.choice(normal_symptoms),
            "sensor_status": "Normal",
            "category": "Normal"
        })

    # 2. Medium-risk observations (~30 records)
    medium_symptoms = [
        "Incision site feels unusually warm to touch",
        "Moderate throbbing pain radiating slightly",
        "Mild swelling and redness around perimeter",
        "Discomfort increasing when changing posture",
        "Perceived warmth around dressing, tired"
    ]
    for _ in range(30):
        temp_choice = random.choice([
            round(random.uniform(37.5, 38.4), 1),
            round(random.uniform(36.5, 37.4), 1)
        ])
        pain_val = random.randint(4, 6) if temp_choice < 37.5 else random.randint(2, 5)
        wound_val = random.choice(["Redness", "Swelling", "Unknown"])
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": temp_choice,
            "pain_score": pain_val,
            "wound_status": wound_val,
            "symptom_description": random.choice(medium_symptoms),
            "sensor_status": "Normal",
            "category": "Medium-risk"
        })

    # 3. High-risk observations (~30 records)
    high_symptoms = [
        "Severe unrelenting pain unresponsive to oral analgesics",
        "Purulent yellowish discharge observed soaking dressing",
        "Active bleeding noted pooling at incision site",
        "Severe throbbing, chills, and patient appearing lethargic",
        "Incision edge separation with severe local burning pain"
    ]
    for _ in range(30):
        temp_val = round(random.uniform(38.5, 39.8), 1) if random.random() > 0.3 else round(random.uniform(36.8, 38.0), 1)
        pain_val = random.randint(7, 10) if temp_val < 38.5 else random.randint(5, 10)
        wound_val = random.choice(["Discharge", "Bleeding", "Swelling"])
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": temp_val,
            "pain_score": pain_val,
            "wound_status": wound_val,
            "symptom_description": random.choice(high_symptoms),
            "sensor_status": "Normal",
            "category": "High-risk"
        })

    # 4. Conflicting observations (~25 records)
    # Sensor says normal temp (36.4 - 37.1°C), but patient reports severe fever, rigors, or shivering
    conflict_symptoms = [
        "Patient complains of high fever, rigors, and teeth-chattering chills",
        "Feeling burning hot with intense shivering despite normal skin probe",
        "Patient reports extreme fever sensation and profuse sweats",
        "Severe chills and sweating reported, but sensor shows baseline normal",
        "Patient feels burning hot with hot flashes and headache"
    ]
    for _ in range(25):
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": round(random.uniform(36.4, 37.1), 1),
            "pain_score": random.randint(2, 6),
            "wound_status": random.choice(["Normal", "Redness"]),
            "symptom_description": random.choice(conflict_symptoms),
            "sensor_status": "Normal",
            "category": "Conflicting"
        })

    # 5. Missing sensor data (~20 records)
    missing_symptoms = [
        "Temperature patch detached during sleep; unmonitored period",
        "Sensor adhesive peeled off skin; telemetry dropped",
        "Patch removed prior to showering and not replaced",
        "Wireless sensor dropped offline; missing temperature stream",
        "Patient reports moderate incision soreness while sensor disconnected"
    ]
    for _ in range(20):
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": np.nan,
            "pain_score": random.randint(1, 8),
            "wound_status": random.choice(["Normal", "Redness", "Swelling", "Discharge"]),
            "symptom_description": random.choice(missing_symptoms),
            "sensor_status": "Missing",
            "category": "Missing sensor"
        })

    # 6. Noisy sensor data (~20 records)
    noisy_symptoms = [
        "Sensor transmitting erratic spikes and artifacts",
        "Loose contact causing rapid jumping temperature readings",
        "Erratic telemetry reading with frequent packet drop",
        "Intermittent sensor noise logged by gateway",
        "Patch partially unseated causing noisy fluctuations"
    ]
    for _ in range(20):
        erratic_temp = round(random.choice([
            random.uniform(28.0, 32.5),  # Unphysiologically low
            random.uniform(43.0, 48.0)   # Unphysiologically high
        ]), 1)
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": erratic_temp,
            "pain_score": random.randint(2, 7),
            "wound_status": random.choice(["Normal", "Redness", "Swelling"]),
            "symptom_description": random.choice(noisy_symptoms),
            "sensor_status": "Noisy",
            "category": "Noisy sensor"
        })

    # Shuffle to simulate realistic interleaved stream
    random.shuffle(records)

    # Required output fields:
    # patient_code, temperature, pain_score, wound_status, symptom_description, sensor_status
    df = pd.DataFrame(records)
    # Retain the exact required columns for the CSV
    output_cols = [
        "patient_code",
        "temperature",
        "pain_score",
        "wound_status",
        "symptom_description",
        "sensor_status"
    ]
    return df[output_cols]


def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "simulated_observations.csv")

    df = generate_simulated_dataset(total_records=155)
    df.to_csv(output_file, index=False)
    print(f"Successfully generated {len(df)} simulated observation records.")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
