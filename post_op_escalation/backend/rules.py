import math
from typing import Optional, Dict, Any


def evaluate_observation(
    temperature: Optional[float],
    pain_score: int,
    wound_status: str,
    symptom_description: Optional[str] = None,
    sensor_status: str = "Normal"
) -> Dict[str, str]:
    """
    Rule-based assessment of post-operative patient observations.

    Pure deterministic logic for risk triage and sensor data quality evaluation.
    Does NOT use machine learning or LLMs.
    Does NOT provide medical diagnoses or autonomous treatment decisions.

    Parameters:
    - temperature: Body temperature in Celsius (float or None if sensor missing)
    - pain_score: Patient-reported pain rating (0-10)
    - wound_status: 'Normal', 'Redness', 'Swelling', 'Discharge', 'Bleeding', 'Unknown'
    - symptom_description: Qualitative symptom notes reported by the patient
    - sensor_status: 'Normal', 'Noisy', 'Missing'

    Returns:
    - Dict with 'risk_level', 'reason', and 'recommendation'.
      Allowed risk levels: LOW, MEDIUM, HIGH, CONFLICT.
    """
    # Normalize inputs
    wound = (wound_status or "Unknown").strip().capitalize()
    sensor = (sensor_status or "Normal").strip().capitalize()
    symptoms = (symptom_description or "").strip().lower()

    # Handle float NaN or None for temperature
    has_valid_temp = (
        temperature is not None
        and not (isinstance(temperature, float) and math.isnan(temperature))
    )
    temp_val = float(temperature) if has_valid_temp else None

    # Keywords suggesting patient-reported systemic symptoms or fever
    concerning_symptom_keywords = [
        "fever", "chills", "shivering", "burning", "hot", "sweat",
        "dizziness", "nausea", "throbbing", "severe", "foul"
    ]
    has_concerning_symptoms = any(kw in symptoms for kw in concerning_symptom_keywords)

    reasons = []

    # 1. CONFLICT DETECTION
    # Discrepancy where sensor reports a normal reading, but patient observations
    # or qualitative reports indicate severe discordance (e.g. sensor reads 36.6°C but
    # patient reports fever/chills or active bleeding).
    if sensor == "Normal" and temp_val is not None and 36.0 <= temp_val <= 37.4:
        if has_concerning_symptoms and any(kw in symptoms for kw in ["fever", "chills", "shivering", "hot"]):
            return {
                "risk_level": "CONFLICT",
                "reason": (
                    f"Conflict detected: Temperature sensor reports normal body temperature ({temp_val:.1f}°C), "
                    f"yet patient reports fever-like symptoms ('{symptom_description}')."
                ),
                "recommendation": (
                    "Clinician review required. Verify sensor placement and calibrate/re-check temperature reading manually."
                )
            }

    # 2. SENSOR INTEGRITY / QUALITY LIMITATION
    sensor_warning = None
    if sensor == "Missing" or not has_valid_temp:
        sensor_warning = "Sensor temperature is missing"
    elif sensor == "Noisy":
        sensor_warning = (
            f"Sensor status is marked as noisy/unreliable (reading: {temp_val:.1f}°C)"
            if temp_val is not None
            else "Sensor is reporting noisy/unreliable data"
        )

    # 3. CLINICAL SEVERITY CHECKS

    # High Severity Indicators
    is_high_temp = has_valid_temp and sensor == "Normal" and (temp_val >= 38.5 or temp_val < 35.0)
    is_high_pain = pain_score >= 7
    is_high_wound = wound in ["Discharge", "Bleeding"]

    if is_high_temp:
        reasons.append(f"Severely abnormal temperature recorded ({temp_val:.1f}°C)")
    if is_high_pain:
        reasons.append(f"Severe pain level reported ({pain_score}/10)")
    if is_high_wound:
        reasons.append(f"Critical wound observation noted ({wound})")

    if is_high_temp or is_high_pain or is_high_wound:
        if sensor_warning:
            reasons.append(f"Data quality limitation: {sensor_warning} Evaluation based on remaining clinical reports.")
        
        return {
            "risk_level": "HIGH",
            "reason": ". ".join(reasons) + ".",
            "recommendation": (
                "Clinician review is required. Prompt clinical evaluation and physical assessment recommended."
            )
        }

    # Medium Severity Indicators
    is_med_temp = has_valid_temp and sensor == "Normal" and (37.5 <= temp_val < 38.5 or 35.0 <= temp_val < 36.0)
    is_med_pain = 4 <= pain_score <= 6
    is_med_wound = wound in ["Redness", "Swelling", "Unknown"]

    if is_med_temp:
        reasons.append(f"Moderately elevated/abnormal temperature recorded ({temp_val:.1f}°C)")
    if is_med_pain:
        reasons.append(f"Moderate pain level reported ({pain_score}/10)")
    if is_med_wound:
        reasons.append(f"Minor or uncertain wound concern noted ({wound})")
    if has_concerning_symptoms and not reasons:
        reasons.append(f"Patient reported concerning symptoms: '{symptom_description}'")

    if is_med_temp or is_med_pain or is_med_wound or (sensor_warning and (pain_score > 0 or wound != "Normal")):
        if sensor_warning:
            reasons.append(f"Data quality limitation: {sensor_warning}")
        return {
            "risk_level": "MEDIUM",
            "reason": ". ".join(reasons) + ".",
            "recommendation": (
                "Follow-up recommended. Monitor patient status and re-assess observations within 4 to 6 hours."
            )
        }

    # If sensor has issues but pain is 0-3 and wound is Normal
    if sensor_warning:
        return {
            "risk_level": "MEDIUM" if sensor == "Missing" else "LOW",
            "reason": (
                f"Data quality limitation: {sensor_warning} Patient reports low pain ({pain_score}/10) "
                f"and normal wound condition."
            ),
            "recommendation": (
                "Request sensor re-attachment or manual vital signs check to confirm physiological baseline."
            )
        }

    # 4. LOW RISK (Baseline normal)
    return {
        "risk_level": "LOW",
        "reason": (
            f"All vital observations within expected recovery baseline: "
            f"Temperature normal ({temp_val:.1f}°C), pain low ({pain_score}/10), wound condition normal."
        ),
        "recommendation": "Continue standard routine post-operative monitoring protocol."
    }
