"""
Test Suite for Store-and-Forward Telemetry & No-Unresolved-High-Priority-Action Guarantee.

Requirements 8 & 9:
1. Normal communication: data generated -> processed -> communicated -> action recorded.
2. Communication failure: data generated -> communication unavailable -> stored locally/queued -> fallback action recorded.
3. Recovery: communication restored -> queued data forwarded -> queue cleared/marked processed -> action recorded.
4. No-Unresolved-High-Priority-Action Guarantee:
   - High-risk + communication available
   - High-risk + communication unavailable
   - High-risk + retry failure
   - High-risk + fallback path
   - High-risk + delayed communication recovery
"""
import pytest
from backend.store_and_forward import StoreAndForwardManager


def test_normal_communication_lifecycle():
    """Verify normal telemetry generation, transmission, and action audit trail."""
    manager = StoreAndForwardManager()
    record = {
        "patient_code": "PAT-001",
        "temperature": 36.8,
        "pain_score": 2,
        "wound_status": "Normal",
        "symptom_description": "Resting comfortably",
        "sensor_status": "Normal"
    }

    result = manager.submit_observation(record, is_communication_available=True)

    assert result["success"] is True
    assert result["status"] == "COMMUNICATED"
    assert result["action_recorded"]["channel"] == "PRIMARY_API"
    assert result["assessment"]["risk_level"] == "LOW"
    assert len(manager.local_queue) == 0  # Not queued because network is available
    assert len(manager.audit_log) == 1


def test_communication_failure_and_store_and_forward():
    """Verify that network outage routes telemetry into local store-and-forward queue."""
    manager = StoreAndForwardManager()
    record = {
        "patient_code": "PAT-002",
        "temperature": 37.0,
        "pain_score": 2,
        "wound_status": "Normal",
        "symptom_description": "Telemetry buffer test",
        "sensor_status": "Normal"
    }

    result = manager.submit_observation(record, is_communication_available=False)

    assert result["success"] is False
    assert result["status"] == "QUEUED"
    assert result["action_recorded"]["channel"] == "LOCAL_STORE_AND_FORWARD_QUEUE"
    assert len(manager.local_queue) == 1
    item_id = result["item_id"]
    assert manager.local_queue[item_id]["status"] == "QUEUED"


def test_communication_recovery_and_queue_flushing():
    """Verify that network restoration flushes queued items in priority order and marks them resolved."""
    manager = StoreAndForwardManager()
    
    # Queue a normal record
    manager.submit_observation({
        "patient_code": "PAT-003",
        "temperature": 36.7,
        "pain_score": 1,
        "wound_status": "Normal",
        "symptom_description": "Normal patient",
        "sensor_status": "Normal"
    }, is_communication_available=False)

    # Queue a high-risk record
    manager.submit_observation({
        "patient_code": "PAT-004",
        "temperature": 39.2,
        "pain_score": 8,
        "wound_status": "Discharge",
        "symptom_description": "Severe pain and fever",
        "sensor_status": "Normal"
    }, is_communication_available=False)

    assert len(manager.local_queue) == 2

    # Restore communication
    recovery_result = manager.restore_communication_and_forward()

    assert recovery_result["recovered"] is True
    assert recovery_result["forwarded_count"] == 2
    assert recovery_result["remaining_unprocessed"] == 0

    # Verify priority ordering: HIGH priority forwarded first
    forwarded_items = recovery_result["forwarded_items"]
    assert forwarded_items[0]["priority"] == "HIGH"
    assert forwarded_items[0]["patient_code"] == "PAT-004"
    assert forwarded_items[1]["priority"] == "NORMAL"
    assert forwarded_items[1]["patient_code"] == "PAT-003"


# --------------------------------------------------------------------------
# Requirement 9: No-Unresolved-High-Priority-Action Guarantee Test Cases
# --------------------------------------------------------------------------
def test_guarantee_1_high_risk_communication_available():
    """Case 1: High-risk patient + communication available -> Immediately communicated."""
    manager = StoreAndForwardManager()
    record = {
        "patient_code": "PAT-010",
        "temperature": 39.5,
        "pain_score": 9,
        "wound_status": "Bleeding",
        "symptom_description": "Active bleeding",
        "sensor_status": "Normal"
    }
    result = manager.submit_observation(record, is_communication_available=True)
    assert result["status"] == "COMMUNICATED"
    assert result["assessment"]["risk_level"] == "HIGH"
    assert manager.verify_no_unresolved_high_priority_actions() is True


def test_guarantee_2_high_risk_communication_unavailable():
    """Case 2: High-risk patient + communication unavailable -> Local queue + immediate fallback engaged."""
    manager = StoreAndForwardManager()
    record = {
        "patient_code": "PAT-011",
        "temperature": 39.4,
        "pain_score": 8,
        "wound_status": "Discharge",
        "symptom_description": "High fever",
        "sensor_status": "Normal"
    }
    result = manager.submit_observation(record, is_communication_available=False)
    assert result["status"] == "QUEUED"
    assert result["fallback_engaged"] is True
    assert result["action_recorded"]["fallback_action_recorded"] is True
    assert result["action_recorded"]["fallback_details"]["fallback_mechanism"] == "LOCAL_CRITICAL_PAGER_ALERT"
    # Even while queued, it has active fallback so it is NOT silently dropped
    assert manager.verify_no_unresolved_high_priority_actions() is True


def test_guarantee_3_high_risk_retry_failure():
    """Case 3: High-risk patient + retry failure -> Escalates to secondary failover channel."""
    manager = StoreAndForwardManager(max_retries=2)
    record = {
        "patient_code": "PAT-012",
        "temperature": 39.0,
        "pain_score": 9,
        "wound_status": "Bleeding",
        "symptom_description": "Active bleeding",
        "sensor_status": "Normal"
    }
    sub = manager.submit_observation(record, is_communication_available=False)
    item_id = sub["item_id"]

    # First retry while network is still down
    manager.retry_pending_queue(is_communication_available=False)
    assert manager.local_queue[item_id]["retry_count"] == 1

    # Second retry breaches max_retries
    manager.retry_pending_queue(is_communication_available=False)
    assert manager.local_queue[item_id]["status"] == "FAILOVER_ESCALATED"
    assert manager.local_queue[item_id]["fallback_details"]["status"] == "SECONDARY_FAILOVER_ENGAGED"
    # Never dropped
    assert manager.verify_no_unresolved_high_priority_actions() is True


def test_guarantee_4_high_risk_fallback_path():
    """Case 4: High-risk patient + fallback path verified end-to-end."""
    manager = StoreAndForwardManager()
    record = {
        "patient_code": "PAT-013",
        "temperature": 37.0,
        "pain_score": 10,
        "wound_status": "Normal",
        "symptom_description": "Severe unrelenting pain unresponsive to analgesics",
        "sensor_status": "Normal"
    }
    res = manager.submit_observation(record, is_communication_available=False)
    assert res["assessment"]["risk_level"] == "HIGH"
    assert res["fallback_engaged"] is True
    item = manager.local_queue[res["item_id"]]
    assert item["fallback_details"]["resolution_path"] == "ACTIVE_LOCAL_CLINICAL_DISPATCH"
    assert manager.verify_no_unresolved_high_priority_actions() is True


def test_guarantee_5_high_risk_delayed_communication_recovery():
    """Case 5: High-risk patient + delayed communication recovery -> Full sync and resolution."""
    manager = StoreAndForwardManager()
    record = {
        "patient_code": "PAT-014",
        "temperature": 39.6,
        "pain_score": 9,
        "wound_status": "Discharge",
        "symptom_description": "Severe surgical site infection signs",
        "sensor_status": "Normal"
    }
    # Initially offline
    res = manager.submit_observation(record, is_communication_available=False)
    item_id = res["item_id"]
    assert manager.local_queue[item_id]["is_resolved"] is False

    # Simulate network retries
    manager.retry_pending_queue(is_communication_available=False)

    # Delayed recovery
    rec = manager.restore_communication_and_forward()
    assert rec["forwarded_count"] == 1
    assert manager.local_queue[item_id]["is_resolved"] is True
    assert manager.local_queue[item_id]["status"] == "FORWARDED"
    assert manager.verify_no_unresolved_high_priority_actions() is True
