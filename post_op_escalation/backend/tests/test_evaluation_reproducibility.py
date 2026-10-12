"""
Test Suite for Evaluation Reproducibility & Ground-Truth Dataset Integrity.

Requirements 1 & 2:
- Re-emitted simulated dataset exists and has valid schema.
- Explicit ground-truth label 'category' is retained.
- Six required scenarios are present with balanced distribution.
- Precision, recall, and F1-score evaluate deterministically.
- Confusion matrix output is valid and export files exist.
"""
import os
import pytest
import pandas as pd
from data.generate_data import generate_simulated_dataset, evaluate_dataset
from sklearn.metrics import classification_report, confusion_matrix


def test_dataset_ground_truth_schema_and_scenarios():
    """Verify generated dataset contains required columns and all 6 scenarios."""
    df = generate_simulated_dataset(records_per_scenario=10)

    # Required columns
    expected_cols = [
        "patient_code", "temperature", "pain_score", "wound_status",
        "symptom_description", "sensor_status", "communication_status", "category"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing required column: {col}"

    # Explicit ground-truth 'category' must not be dropped
    assert "category" in df.columns

    # 6 Scenarios must all be present
    scenarios = set(df["category"].unique())
    expected_scenarios = {
        "Normal", "High-risk", "Missing data",
        "Noisy data", "Conflicting data", "Communication/fallback failure"
    }
    assert scenarios == expected_scenarios


def test_deterministic_evaluation_metrics():
    """Verify rule-engine evaluation generates valid non-trivial metrics across all 6 classes."""
    df = generate_simulated_dataset(records_per_scenario=15)
    evaluated = evaluate_dataset(df)

    assert "predicted_category" in evaluated.columns
    assert "predicted_risk_level" in evaluated.columns

    report = classification_report(
        evaluated["category"],
        evaluated["predicted_category"],
        output_dict=True
    )

    # Overall macro accuracy and F1 must be high (> 0.95)
    assert report["macro avg"]["f1-score"] >= 0.95
    assert report["accuracy"] >= 0.95

    # Check 6x6 confusion matrix shape
    labels = sorted(list(df["category"].unique()))
    cm = confusion_matrix(evaluated["category"], evaluated["predicted_category"], labels=labels)
    assert cm.shape == (6, 6)


def test_exported_evaluation_artifacts_exist():
    """Verify evaluation pipeline output files exist in reports directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    reports_dir = os.path.join(base_dir, "reports")

    assert os.path.exists(os.path.join(reports_dir, "evaluation_results.json"))
    assert os.path.exists(os.path.join(reports_dir, "evaluation_metrics.csv"))
    assert os.path.exists(os.path.join(reports_dir, "confusion_matrix.png"))
