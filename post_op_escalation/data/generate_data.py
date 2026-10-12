"""
Synthetic Dataset Generator for Post-Operative Patient Monitoring.

Generates reproducible post-operative observation records with explicit ground-truth labels
across the six required clinical and telemetry scenarios:
1. Normal
2. High-risk
3. Missing data
4. Noisy data
5. Conflicting data
6. Communication/fallback failure

Retains the explicit ground-truth column: 'category'.
"""
import os
import random
import numpy as np
import pandas as pd

# Fixed random seed for deterministic reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

WOUND_STATUSES = ["Normal", "Redness", "Swelling", "Discharge", "Bleeding", "Unknown"]
SENSOR_STATUSES = ["Normal", "Noisy", "Missing"]
COMMUNICATION_STATUSES = ["Normal", "Failed"]


def generate_simulated_dataset(records_per_scenario: int = 30) -> pd.DataFrame:
    """
    Generate synthetic post-operative patient observations across 6 distinct evaluation categories:
    1. Normal
    2. High-risk
    3. Missing data
    4. Noisy data
    5. Conflicting data
    6. Communication/fallback failure

    Explicitly preserves the ground-truth 'category' column.
    """
    records = []
    patient_pool = [f"PAT-{i:03d}" for i in range(1, 36)]

    # 1. Normal observations (Baseline recovery)
    normal_symptoms = [
        "Patient resting comfortably, no acute distress",
        "Mild surgical site soreness, expected post-op",
        "Walking around room with minimal discomfort",
        "Dressing clean and intact, pain well-managed",
        "Tolerating oral intake, sleeping well"
    ]
    for _ in range(records_per_scenario):
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": round(random.uniform(36.4, 37.2), 1),
            "pain_score": random.randint(0, 3),
            "wound_status": "Normal",
            "symptom_description": random.choice(normal_symptoms),
            "sensor_status": "Normal",
            "communication_status": "Normal",
            "category": "Normal"
        })

    # 2. High-risk observations (Acute clinical severity)
    high_symptoms = [
        "Severe unrelenting pain unresponsive to oral analgesics",
        "Purulent yellowish discharge observed soaking dressing",
        "Active bleeding noted pooling at incision site",
        "Severe throbbing incision pain and patient appearing lethargic",
        "Incision edge separation with severe local burning pain"
    ]
    for _ in range(records_per_scenario):
        # High temp (>= 38.5) or High pain (>= 7) or Critical wound (Discharge/Bleeding)
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
            "communication_status": "Normal",
            "category": "High-risk"
        })

    # 3. Missing data (Telemetry sensor absent/detached)
    missing_symptoms = [
        "Temperature patch detached during sleep; unmonitored period",
        "Sensor adhesive peeled off skin; telemetry dropped",
        "Patch removed prior to showering and not replaced",
        "Wireless sensor dropped offline; missing temperature stream",
        "Patch disconnected; telemetry stream empty"
    ]
    for _ in range(records_per_scenario):
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": np.nan,
            "pain_score": random.randint(0, 3),
            "wound_status": "Normal",
            "symptom_description": random.choice(missing_symptoms),
            "sensor_status": "Missing",
            "communication_status": "Normal",
            "category": "Missing data"
        })

    # 4. Noisy data (Telemetry artifacts / unphysiological readings)
    noisy_symptoms = [
        "Sensor transmitting erratic spikes and artifacts",
        "Loose contact causing rapid jumping temperature readings",
        "Erratic telemetry reading with frequent packet drop",
        "Intermittent sensor noise logged by gateway",
        "Patch partially unseated causing noisy fluctuations"
    ]
    for _ in range(records_per_scenario):
        erratic_temp = round(random.choice([
            random.uniform(28.0, 32.5),  # Unphysiologically low
            random.uniform(43.0, 48.0)   # Unphysiologically high
        ]), 1)
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": erratic_temp,
            "pain_score": random.randint(0, 3),
            "wound_status": "Normal",
            "symptom_description": random.choice(noisy_symptoms),
            "sensor_status": "Noisy",
            "communication_status": "Normal",
            "category": "Noisy data"
        })

    # 5. Conflicting data (Objective baseline vs subjective fever/chills symptoms)
    conflict_symptoms = [
        "Patient complains of high fever, rigors, and teeth-chattering chills",
        "Feeling burning hot with intense shivering despite normal skin probe",
        "Patient reports extreme fever sensation and profuse sweats",
        "Severe chills and sweating reported, but sensor shows baseline normal",
        "Patient feels burning hot with hot flashes and headache"
    ]
    for _ in range(records_per_scenario):
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": round(random.uniform(36.4, 37.1), 1),
            "pain_score": random.randint(1, 4),
            "wound_status": "Normal",
            "symptom_description": random.choice(conflict_symptoms),
            "sensor_status": "Normal",
            "communication_status": "Normal",
            "category": "Conflicting data"
        })

    # 6. Communication/fallback failure (Gateway unreachable, store-and-forward engaged)
    fallback_symptoms = [
        "Telemetry gateway unreachable, transmission timeout occurred",
        "Cellular uplink failed, queuing report for store-and-forward",
        "Network interface connection refused; fallback dispatch initiated",
        "Primary telemetry offline; transmission failed",
        "Gateway unreachable; local queue buffering active"
    ]
    for _ in range(records_per_scenario):
        records.append({
            "patient_code": random.choice(patient_pool),
            "temperature": round(random.uniform(36.6, 37.8), 1),
            "pain_score": random.randint(1, 5),
            "wound_status": random.choice(["Normal", "Redness"]),
            "symptom_description": random.choice(fallback_symptoms),
            "sensor_status": "Normal",
            "communication_status": "Failed",
            "category": "Communication/fallback failure"
        })

    # Deterministic shuffle with fixed seed
    rng = random.Random(RANDOM_SEED)
    rng.shuffle(records)

    df = pd.DataFrame(records)

    # Required output columns explicitly retaining ground-truth 'category'
    output_cols = [
        "patient_code",
        "temperature",
        "pain_score",
        "wound_status",
        "symptom_description",
        "sensor_status",
        "communication_status",
        "category"
    ]
    return df[output_cols]


def evaluate_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply pure rule-based risk evaluation across all records in the simulated dataset.
    Generates predicted_risk_level and predicted_category for direct evaluation against ground truth.
    """
    from backend.rules import evaluate_observation

    results = []
    for _, row in df.iterrows():
        temp_val = float(row["temperature"]) if pd.notna(row["temperature"]) else None
        eval_res = evaluate_observation(
            temperature=temp_val,
            pain_score=int(row["pain_score"]),
            wound_status=str(row["wound_status"]),
            symptom_description=str(row["symptom_description"]) if pd.notna(row["symptom_description"]) else None,
            sensor_status=str(row["sensor_status"]),
            communication_status=str(row.get("communication_status", "Normal"))
        )
        results.append({
            "predicted_risk_level": eval_res["risk_level"],
            "predicted_category": eval_res["predicted_category"],
            "reason": eval_res["reason"],
            "recommendation": eval_res["recommendation"]
        })

    eval_df = pd.DataFrame(results)
    return pd.concat([df.reset_index(drop=True), eval_df.reset_index(drop=True)], axis=1)


def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "simulated_observations.csv")

    df = generate_simulated_dataset(records_per_scenario=30)
    df.to_csv(output_file, index=False)
    print(f"Successfully generated {len(df)} simulated observation records with ground truth.")
    print(f"Scenarios covered: {sorted(df['category'].unique())}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
