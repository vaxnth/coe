"""
Test Suite for Signal Normalization, Conflict Detection, Consistent Severity Policy & Edge Cases.

Requirements 6, 7, and 10:
- Deterministic signal normalization
- Conflict detection (objective vs subjective discrepancy)
- Consistent severity checks across noisy, missing, and boundary readings
- Edge case coverage (missing values, extreme vitals, threshold boundaries)
"""
import pytest
import math
from backend.rules import evaluate_observation, normalize_symptom_signals


# -------------------------------------------------------------
# 1. Signal Normalization Tests (Requirement 6)
# -------------------------------------------------------------
def test_signal_normalization_temperature_synonyms():
    """Verify various expressions of elevated temperature normalize to 'temperature_high'."""
    assert normalize_symptom_signals("Patient has high fever")["temperature_signal"] == "temperature_high"
    assert normalize_symptom_signals("temperature elevated")["temperature_signal"] == "temperature_high"
    assert normalize_symptom_signals("high temperature recorded at home")["temperature_signal"] == "temperature_high"
    assert normalize_symptom_signals("feeling burning hot with rigors")["temperature_signal"] == "temperature_high"
    assert normalize_symptom_signals("intense shivering and chills")["temperature_signal"] == "temperature_high"
    assert normalize_symptom_signals("profuse sweating and hot flashes")["temperature_signal"] == "temperature_high"


def test_signal_normalization_pain_and_wound_synonyms():
    """Verify pain and wound descriptions normalize correctly."""
    assert normalize_symptom_signals("unrelenting pain in abdomen")["pain_signal"] == "pain_severe"
    assert normalize_symptom_signals("excruciating surgical site pain")["pain_signal"] == "pain_severe"
    assert normalize_symptom_signals("moderate throbbing discomfort")["pain_signal"] == "pain_moderate"
    assert normalize_symptom_signals("minimal discomfort, resting comfortably")["pain_signal"] == "pain_mild"

    assert normalize_symptom_signals("purulent drainage soaked dressing")["wound_signal"] == "wound_critical"
    assert normalize_symptom_signals("active bleeding from incision")["wound_signal"] == "wound_critical"
    assert normalize_symptom_signals("dressing clean and intact")["wound_signal"] == "wound_normal"


# -------------------------------------------------------------
# 2. Conflict Detection Tests (Requirement 6)
# -------------------------------------------------------------
def test_conflict_normal_sensor_temp_vs_fever_symptoms():
    """Objective sensor reads normal (36.6°C), but patient reports fever/chills."""
    res = evaluate_observation(
        temperature=36.6,
        pain_score=2,
        wound_status="Normal",
        symptom_description="Feeling burning hot with rigors and high fever",
        sensor_status="Normal"
    )
    assert res["risk_level"] == "CONFLICT"
    assert res["predicted_category"] == "Conflicting data"
    assert "Conflict detected" in res["reason"]


def test_conflict_low_pain_score_vs_severe_pain_description():
    """Objective pain score entered as 0, but text reports excruciating agony."""
    res = evaluate_observation(
        temperature=36.8,
        pain_score=0,
        wound_status="Normal",
        symptom_description="Severe unrelenting pain, excruciating agony",
        sensor_status="Normal"
    )
    assert res["risk_level"] == "CONFLICT"
    assert res["predicted_category"] == "Conflicting data"


def test_conflict_normal_wound_status_vs_purulent_discharge():
    """Wound status entered as Normal, but qualitative notes state active purulent discharge."""
    res = evaluate_observation(
        temperature=36.9,
        pain_score=2,
        wound_status="Normal",
        symptom_description="Incision leaking purulent yellowish pus",
        sensor_status="Normal"
    )
    assert res["risk_level"] == "CONFLICT"
    assert res["predicted_category"] == "Conflicting data"


# -------------------------------------------------------------
# 3. Severity Consistency & Noisy Sensor Safety (Requirement 7)
# -------------------------------------------------------------
def test_noisy_reading_cannot_bypass_critical_temperature():
    """
    CRITICAL SAFETY REQUIREMENT:
    A noisy high-temperature reading (e.g. 39.5°C or 44.0°C) must NOT bypass high-severity triage.
    """
    res = evaluate_observation(
        temperature=39.5,
        pain_score=2,
        wound_status="Normal",
        symptom_description="Sensor unstable telemetry",
        sensor_status="Noisy"
    )
    assert res["risk_level"] == "HIGH"
    assert res["predicted_category"] == "Noisy data"
    assert "Critical temperature threshold breach" in res["reason"]


def test_noisy_reading_normal_temp_is_medium_quality_warning():
    """A noisy sensor reading within normal temperature range triggers data quality limitation."""
    res = evaluate_observation(
        temperature=36.8,
        pain_score=2,
        wound_status="Normal",
        symptom_description="Minor telemetry noise",
        sensor_status="Noisy"
    )
    assert res["risk_level"] == "MEDIUM"
    assert res["predicted_category"] == "Noisy data"
    assert "Data quality limitation" in res["reason"]


def test_missing_temperature_handling():
    """Missing temperature reading (null or NaN) flagged gracefully as data quality limitation."""
    res_none = evaluate_observation(
        temperature=None,
        pain_score=2,
        wound_status="Normal",
        symptom_description="Sensor unattached",
        sensor_status="Missing"
    )
    assert res_none["risk_level"] == "MEDIUM"
    assert res_none["predicted_category"] == "Missing data"

    res_nan = evaluate_observation(
        temperature=float("nan"),
        pain_score=2,
        wound_status="Normal",
        symptom_description="Sensor detached",
        sensor_status="Missing"
    )
    assert res_nan["risk_level"] == "MEDIUM"
    assert res_nan["predicted_category"] == "Missing data"


def test_missing_sensor_with_high_pain_escalates_to_high():
    """When temperature is missing but pain is severe (9/10), high risk must be triggered."""
    res = evaluate_observation(
        temperature=None,
        pain_score=9,
        wound_status="Normal",
        symptom_description="Severe acute incision pain",
        sensor_status="Missing"
    )
    assert res["risk_level"] == "HIGH"
    assert res["predicted_category"] == "Missing data"
    assert "Severe pain level reported (9/10)" in res["reason"]


# -------------------------------------------------------------
# 4. Boundary Threshold Value Testing (Requirement 10)
# -------------------------------------------------------------
@pytest.mark.parametrize("temp,expected_risk", [
    (34.9, "HIGH"),     # Severe hypothermia
    (35.0, "MEDIUM"),   # Mild hypothermia boundary
    (35.9, "MEDIUM"),   # Borderline low
    (36.0, "LOW"),      # Normal range lower bound
    (37.4, "LOW"),      # Normal range upper bound
    (37.5, "MEDIUM"),   # Low-grade elevation threshold
    (38.4, "MEDIUM"),   # High-grade boundary lower edge
    (38.5, "HIGH"),     # High pyrexia threshold
    (40.0, "HIGH"),     # Severe hyperpyrexia
])
def test_temperature_boundary_thresholds(temp, expected_risk):
    """Verify deterministic boundary transitions for body temperature."""
    res = evaluate_observation(
        temperature=temp,
        pain_score=1,
        wound_status="Normal",
        symptom_description=None,
        sensor_status="Normal"
    )
    assert res["risk_level"] == expected_risk


@pytest.mark.parametrize("pain,expected_risk", [
    (0, "LOW"),
    (3, "LOW"),
    (4, "MEDIUM"),
    (6, "MEDIUM"),
    (7, "HIGH"),
    (10, "HIGH"),
])
def test_pain_boundary_thresholds(pain, expected_risk):
    """Verify deterministic boundary transitions for pain scores."""
    res = evaluate_observation(
        temperature=36.8,
        pain_score=pain,
        wound_status="Normal",
        symptom_description=None,
        sensor_status="Normal"
    )
    assert res["risk_level"] == expected_risk


@pytest.mark.parametrize("wound,expected_risk", [
    ("Normal", "LOW"),
    ("Redness", "MEDIUM"),
    ("Swelling", "MEDIUM"),
    ("Unknown", "MEDIUM"),
    ("Discharge", "HIGH"),
    ("Bleeding", "HIGH"),
])
def test_wound_status_categories(wound, expected_risk):
    """Verify wound status categorization matches clinical severity policy."""
    res = evaluate_observation(
        temperature=36.8,
        pain_score=2,
        wound_status=wound,
        symptom_description=None,
        sensor_status="Normal"
    )
    assert res["risk_level"] == expected_risk
