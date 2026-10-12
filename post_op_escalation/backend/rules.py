import math
from typing import Optional, Dict, Any


def normalize_symptom_signals(symptom_description: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Normalize raw patient symptom descriptions and text reports into structured semantic signals.

    Conceptual flow:
    Raw input -> Lowercase/clean -> Match semantic synonym groups -> Structured signals.
    """
    if not symptom_description:
        return {
            "temperature_signal": None,
            "pain_signal": None,
            "wound_signal": None,
            "communication_signal": None
        }

    text = symptom_description.strip().lower()

    # 1. Temperature-related normalized signals
    temp_high_synonyms = [
        "fever", "high temperature", "temperature elevated", "elevated temp",
        "elevated temperature", "burning hot", "burning", "febrile", "chills",
        "rigors", "shivering", "profuse sweat", "sweating", "hot flashes",
        "pyrexia", "teeth-chattering", "feeling hot"
    ]
    temp_normal_synonyms = [
        "temperature normal", "normal temp", "no fever", "afebrile",
        "feeling cool", "temp baseline"
    ]

    temp_signal = None
    if any(s in text for s in temp_high_synonyms):
        temp_signal = "temperature_high"
    elif any(s in text for s in temp_normal_synonyms):
        temp_signal = "temperature_normal"

    # 2. Pain-related normalized signals
    pain_severe_synonyms = [
        "severe pain", "unrelenting pain", "extreme pain", "worst pain",
        "severe throbbing", "unbearable", "excruciating",
        "agonizing", "screaming in pain", "severe local burning pain"
    ]
    pain_moderate_synonyms = [
        "moderate pain", "moderate discomfort", "unusually warm",
        "discomfort increasing", "moderate throbbing", "throbbing"
    ]
    pain_mild_synonyms = [
        "mild soreness", "mild pain", "minimal discomfort",
        "well-managed", "comfortable", "no acute distress", "resting comfortably"
    ]

    pain_signal = None
    if any(s in text for s in pain_severe_synonyms):
        pain_signal = "pain_severe"
    elif any(s in text for s in pain_moderate_synonyms):
        pain_signal = "pain_moderate"
    elif any(s in text for s in pain_mild_synonyms):
        pain_signal = "pain_mild"

    # 3. Wound-related normalized signals
    wound_critical_synonyms = [
        "purulent", "yellowish discharge", "discharge", "oozing pus",
        "active bleeding", "bleeding", "pooling", "incision edge separation",
        "separation", "dehiscence", "wound opened"
    ]
    wound_concerning_synonyms = [
        "swelling", "redness", "warm to touch", "inflammation", "erythema"
    ]
    wound_normal_synonyms = [
        "clean and intact", "dressing clean", "clean", "dry", "healing well"
    ]

    wound_signal = None
    if any(s in text for s in wound_critical_synonyms):
        wound_signal = "wound_critical"
    elif any(s in text for s in wound_concerning_synonyms):
        wound_signal = "wound_concerning"
    elif any(s in text for s in wound_normal_synonyms):
        wound_signal = "wound_normal"

    # 4. Communication & Telemetry signals
    comm_failure_synonyms = [
        "gateway unreachable", "transmission timeout", "cellular uplink failed",
        "connection refused", "fallback dispatch", "network offline",
        "gateway offline", "communication failure", "primary telemetry offline"
    ]
    comm_signal = None
    if any(s in text for s in comm_failure_synonyms):
        comm_signal = "communication_failed"

    return {
        "temperature_signal": temp_signal,
        "pain_signal": pain_signal,
        "wound_signal": wound_signal,
        "communication_signal": comm_signal
    }


def evaluate_observation(
    temperature: Optional[float],
    pain_score: int,
    wound_status: str,
    symptom_description: Optional[str] = None,
    sensor_status: str = "Normal",
    communication_status: str = "Normal"
) -> Dict[str, Any]:
    """
    Deterministic rule-based assessment and triage of post-operative patient observations.

    Rule ordering & safety policy:
    1. Communication / Fallback Check: Gateway outages engage fallback triage immediately.
    2. Conflict Detection: Discrepancy between normalized symptom signals and objective vitals.
    3. Clinical High-Severity Check: High pain, critical wound, or high temperature.
       * Safety Guarantee: Noisy readings with critical thresholds NEVER bypass high-severity alerts.
    4. Sensor Quality / Telemetry Limitation: Missing or noisy sensor data flagged with quality warnings.
    5. Moderate Severity Check: Borderline vitals, moderate pain, or minor wound changes.
    6. Normal Baseline: All readings within standard post-operative recovery baseline.

    Returns:
    - risk_level: LOW, MEDIUM, HIGH, CONFLICT
    - predicted_category: Normal, High-risk, Missing data, Noisy data, Conflicting data, Communication/fallback failure
    - reason: Transparent clinical explanation
    - recommendation: Non-diagnostic actionable clinical guidance
    - normalized_signals: Structured representation of qualitative symptoms
    """
    wound = (wound_status or "Unknown").strip().capitalize()
    sensor = (sensor_status or "Normal").strip().capitalize()
    comm = (communication_status or "Normal").strip().capitalize()

    # Handle float NaN or None for temperature
    has_valid_temp = (
        temperature is not None
        and not (isinstance(temperature, float) and math.isnan(temperature))
    )
    temp_val = float(temperature) if has_valid_temp else None

    # Structured signal extraction from raw symptom description
    norm_signals = normalize_symptom_signals(symptom_description)
    temp_sig = norm_signals["temperature_signal"]
    pain_sig = norm_signals["pain_signal"]
    wound_sig = norm_signals["wound_signal"]
    comm_sig = norm_signals["communication_signal"]

    # -------------------------------------------------------------
    # 1. COMMUNICATION / FALLBACK FAILURE HANDLING
    # -------------------------------------------------------------
    if comm in ["Failed", "Offline"] or comm_sig == "communication_failed":
        return {
            "risk_level": "HIGH",
            "predicted_category": "Communication/fallback failure",
            "reason": (
                "Communication failure detected: Telemetry transmission channel is unavailable. "
                "Local store-and-forward queue active; fallback dispatch protocol initiated."
            ),
            "recommendation": (
                "Verify network telemetry gateway. Ensure backup communication path (SMS/cellular/local pager) "
                "is activated for immediate clinical notification."
            ),
            "normalized_signals": norm_signals
        }

    # -------------------------------------------------------------
    # 2. CONFLICT DETECTION (Normalized Objective vs Subjective)
    # -------------------------------------------------------------
    # Case A: Sensor reads normal temperature (36.0 - 37.4°C), but patient reports high temp/fever
    temp_conflict = (
        sensor == "Normal"
        and temp_val is not None
        and 36.0 <= temp_val <= 37.4
        and temp_sig == "temperature_high"
    )

    # Case B: Patient reports 0 or 1 pain score, but qualitative description notes severe pain
    pain_conflict = (
        pain_score <= 1
        and pain_sig == "pain_severe"
    )

    # Case C: Wound marked as Normal, but qualitative description notes active bleeding/discharge
    wound_conflict = (
        wound == "Normal"
        and wound_sig == "wound_critical"
    )

    if temp_conflict or pain_conflict or wound_conflict:
        conflict_details = []
        if temp_conflict:
            conflict_details.append(
                f"Temperature sensor reports normal reading ({temp_val:.1f}°C) while patient reports fever symptoms"
            )
        if pain_conflict:
            conflict_details.append(
                f"Pain score entered as {pain_score}/10 while symptom report indicates severe acute pain"
            )
        if wound_conflict:
            conflict_details.append(
                "Wound entered as 'Normal' while text notes active discharge/bleeding"
            )

        return {
            "risk_level": "CONFLICT",
            "predicted_category": "Conflicting data",
            "reason": (
                f"Conflict detected: {'; '.join(conflict_details)}. Raw notes: '{symptom_description}'."
            ),
            "recommendation": (
                "Clinician review required. Verify sensor placement, calibrate equipment, "
                "and reconcile self-reported discrepancy with direct clinical evaluation."
            ),
            "normalized_signals": norm_signals
        }

    # -------------------------------------------------------------
    # 3. CLINICAL HIGH-SEVERITY CHECKS (Safety-First Policy)
    # -------------------------------------------------------------
    # High Pain
    is_high_pain = pain_score >= 7 or pain_sig == "pain_severe"

    # Critical Wound
    is_critical_wound = wound in ["Discharge", "Bleeding"] or wound_sig == "wound_critical"

    # High / Critical Temperature:
    # Under Normal sensor: >= 38.5°C or < 35.0°C (hypothermia)
    is_high_temp_normal = has_valid_temp and sensor == "Normal" and (temp_val >= 38.5 or temp_val < 35.0)

    # CONSISTENCY GUARANTEE (Requirement 7):
    # A noisy sensor reading with extreme/critical temperature threshold breach
    # must NEVER bypass high severity alerts.
    is_high_temp_noisy = has_valid_temp and sensor == "Noisy" and (temp_val >= 38.5 or temp_val < 35.0)

    high_reasons = []
    if is_high_temp_normal:
        high_reasons.append(f"Severely abnormal temperature recorded ({temp_val:.1f}°C)")
    elif is_high_temp_noisy:
        high_reasons.append(
            f"Data quality limitation: Sensor status is marked as noisy/unreliable (reading: {temp_val:.1f}°C). "
            f"Critical temperature threshold breach detected on noisy sensor channel"
        )

    if is_high_pain:
        high_reasons.append(f"Severe pain level reported ({pain_score}/10)")
    if is_critical_wound:
        high_reasons.append(f"Critical wound observation noted ({wound})")

    if is_high_temp_normal or is_high_temp_noisy or is_high_pain or is_critical_wound:
        if sensor == "Missing" or not has_valid_temp:
            high_reasons.append("Data quality limitation: Sensor temperature is missing")
            pred_cat = "Missing data"
        elif sensor == "Noisy":
            if not is_high_temp_noisy:
                high_reasons.append(f"Data quality limitation: Sensor is marked noisy ({temp_val:.1f}°C)")
            pred_cat = "Noisy data"
        else:
            pred_cat = "High-risk"

        return {
            "risk_level": "HIGH",
            "predicted_category": pred_cat,
            "reason": ". ".join(high_reasons) + ".",
            "recommendation": (
                "Clinician review is required. Prompt clinical evaluation and physical assessment recommended."
            ),
            "normalized_signals": norm_signals
        }

    # -------------------------------------------------------------
    # 4. SENSOR INTEGRITY / QUALITY LIMITATION (Non-High Cases)
    # -------------------------------------------------------------
    if sensor == "Missing" or not has_valid_temp:
        return {
            "risk_level": "MEDIUM",
            "predicted_category": "Missing data",
            "reason": (
                f"Data quality limitation: Sensor temperature is missing. "
                f"Reported pain is {pain_score}/10 and wound is {wound}."
            ),
            "recommendation": (
                "Telemetry re-attachment required. Verify wireless sensor status or perform manual vital check."
            ),
            "normalized_signals": norm_signals
        }

    if sensor == "Noisy":
        return {
            "risk_level": "MEDIUM",
            "predicted_category": "Noisy data",
            "reason": (
                f"Data quality limitation: Sensor status is marked as noisy/unreliable "
                f"(reading: {temp_val:.1f}°C). Baseline physical assessment indicated."
            ),
            "recommendation": (
                "Sensor maintenance or recalibration required. Inspect sensor patch contact and re-check manually."
            ),
            "normalized_signals": norm_signals
        }

    # -------------------------------------------------------------
    # 5. MODERATE SEVERITY CHECKS
    # -------------------------------------------------------------
    is_med_temp = has_valid_temp and (37.5 <= temp_val < 38.5 or 35.0 <= temp_val < 36.0)
    is_med_pain = 4 <= pain_score <= 6 or pain_sig == "pain_moderate"
    is_med_wound = wound in ["Redness", "Swelling", "Unknown"] or wound_sig == "wound_concerning"

    med_reasons = []
    if is_med_temp:
        med_reasons.append(f"Moderately elevated/abnormal temperature recorded ({temp_val:.1f}°C)")
    if is_med_pain:
        med_reasons.append(f"Moderate pain level reported ({pain_score}/10)")
    if is_med_wound:
        med_reasons.append(f"Minor or uncertain wound concern noted ({wound})")
    if temp_sig == "temperature_high" and not is_med_temp:
        med_reasons.append(f"Patient reported temperature warmth notes: '{symptom_description}'")

    if is_med_temp or is_med_pain or is_med_wound or med_reasons:
        return {
            "risk_level": "MEDIUM",
            "predicted_category": "Normal",  # Under standard 6 scenarios, borderline normal/medium vitals
            "reason": ". ".join(med_reasons) + ".",
            "recommendation": (
                "Follow-up recommended. Monitor patient status and re-assess observations within 4 to 6 hours."
            ),
            "normalized_signals": norm_signals
        }

    # -------------------------------------------------------------
    # 6. LOW RISK (Normal Baseline Recovery)
    # -------------------------------------------------------------
    return {
        "risk_level": "LOW",
        "predicted_category": "Normal",
        "reason": (
            f"All vital observations within expected recovery baseline: "
            f"Temperature normal ({temp_val:.1f}°C), pain low ({pain_score}/10), wound condition normal."
        ),
        "recommendation": "Continue standard routine post-operative monitoring protocol.",
        "normalized_signals": norm_signals
    }

