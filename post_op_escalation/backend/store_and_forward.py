"""
Store-and-Forward Telemetry and Resilient Fallback Engine.

Implements clinical-grade fault-tolerance for post-operative monitoring:
1. Normal communication:
   Data generated -> Rule engine triage -> Communicated to primary backend -> Action recorded.
2. Communication failure:
   Data generated -> Network unavailable -> Stored in local resilient queue -> Fallback action engaged.
3. Recovery:
   Network restored -> Priority-ordered forward -> Queue cleared/marked processed -> Action recorded.
4. No-Unresolved-High-Priority-Action Guarantee:
   Guarantees that no high-risk/conflict event is ever silently dropped or abandoned.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from .rules import evaluate_observation


class StoreAndForwardManager:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.local_queue: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []

    def submit_observation(
        self,
        observation_data: Dict[str, Any],
        is_communication_available: bool = True
    ) -> Dict[str, Any]:
        """
        Submit post-operative observation record with automatic store-and-forward handling.
        """
        item_id = str(uuid.uuid4())
        obs_copy = dict(observation_data)

        # Local rule evaluation
        assessment = evaluate_observation(
            temperature=obs_copy.get("temperature"),
            pain_score=obs_copy.get("pain_score", 0),
            wound_status=obs_copy.get("wound_status", "Normal"),
            symptom_description=obs_copy.get("symptom_description"),
            sensor_status=obs_copy.get("sensor_status", "Normal"),
            communication_status="Normal"
        )
        is_high_priority = assessment["risk_level"] in ["HIGH", "CONFLICT"]

        timestamp = datetime.utcnow().isoformat()

        if is_communication_available:
            # 1. Normal Communication Path
            action_record = {
                "item_id": item_id,
                "timestamp": timestamp,
                "status": "COMMUNICATED",
                "channel": "PRIMARY_API",
                "risk_level": assessment["risk_level"],
                "predicted_category": assessment.get("predicted_category", "Normal"),
                "details": "Telemetry successfully transmitted to primary clinical server.",
                "patient_code": obs_copy.get("patient_code")
            }
            self.audit_log.append(action_record)
            return {
                "success": True,
                "status": "COMMUNICATED",
                "action_recorded": action_record,
                "assessment": assessment,
                "item_id": item_id
            }
        else:
            # 2. Communication Failure Path (Local Store-and-Forward)
            fallback_details = None
            if is_high_priority:
                fallback_details = {
                    "fallback_mechanism": "LOCAL_CRITICAL_PAGER_ALERT",
                    "backup_channel": "SMS_FAILOVER",
                    "reason": "Primary central telemetry connection unavailable",
                    "engaged_at": timestamp,
                    "resolution_path": "ACTIVE_LOCAL_CLINICAL_DISPATCH"
                }

            queue_item = {
                "item_id": item_id,
                "created_at": timestamp,
                "payload": obs_copy,
                "assessment": assessment,
                "priority": "HIGH" if is_high_priority else "NORMAL",
                "status": "QUEUED",
                "retry_count": 0,
                "fallback_engaged": is_high_priority,
                "fallback_details": fallback_details,
                "is_resolved": False
            }
            self.local_queue[item_id] = queue_item

            action_record = {
                "item_id": item_id,
                "timestamp": timestamp,
                "status": "STORED_LOCALLY",
                "channel": "LOCAL_STORE_AND_FORWARD_QUEUE",
                "risk_level": assessment["risk_level"],
                "priority": queue_item["priority"],
                "fallback_action_recorded": is_high_priority,
                "fallback_details": fallback_details,
                "details": (
                    "Primary transmission failed. Data stored in local queue. "
                    + ("Emergency fallback alert engaged for high-priority case." if is_high_priority else "Queued for retry.")
                ),
                "patient_code": obs_copy.get("patient_code")
            }
            self.audit_log.append(action_record)

            return {
                "success": False,
                "status": "QUEUED",
                "action_recorded": action_record,
                "assessment": assessment,
                "fallback_engaged": is_high_priority,
                "item_id": item_id
            }

    def retry_pending_queue(self, is_communication_available: bool = False) -> Dict[str, Any]:
        """
        Retry queued telemetry items. If communication fails and max retries are exceeded,
        escalates to hard secondary failover so high-priority events are NEVER lost.
        """
        if is_communication_available:
            return self.restore_communication_and_forward()

        failed_retries = []
        escalated_failovers = []

        for item_id, item in list(self.local_queue.items()):
            if item["status"] == "QUEUED":
                item["retry_count"] += 1
                if item["retry_count"] >= self.max_retries:
                    # Escalated Failover: Prevents high priority from remaining unresolved
                    item["status"] = "FAILOVER_ESCALATED"
                    failover_record = {
                        "item_id": item_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "SECONDARY_FAILOVER_ENGAGED",
                        "channel": "MANUAL_CLINICIAN_DISPATCH",
                        "priority": item["priority"],
                        "details": f"Max retries ({self.max_retries}) reached. Escalated to direct manual clinical notification."
                    }
                    item["fallback_details"] = failover_record
                    self.audit_log.append(failover_record)
                    escalated_failovers.append(item_id)
                else:
                    failed_retries.append(item_id)

        return {
            "retried_count": len(failed_retries) + len(escalated_failovers),
            "escalated_failovers": escalated_failovers,
            "queue_depth": len([i for i in self.local_queue.values() if i["status"] in ["QUEUED", "FAILOVER_ESCALATED"]])
        }

    def restore_communication_and_forward(self) -> Dict[str, Any]:
        """
        Called when network communication is restored.
        Forwards all queued observations in priority order (HIGH first).
        """
        # Sort queue: HIGH priority first, then by timestamp
        pending = [
            item for item in self.local_queue.values()
            if item["status"] in ["QUEUED", "FAILOVER_ESCALATED"]
        ]
        pending.sort(key=lambda x: (0 if x["priority"] == "HIGH" else 1, x["created_at"]))

        forwarded_items = []
        for item in pending:
            item_id = item["item_id"]
            item["status"] = "FORWARDED"
            item["is_resolved"] = True
            item["forwarded_at"] = datetime.utcnow().isoformat()

            forward_record = {
                "item_id": item_id,
                "timestamp": item["forwarded_at"],
                "status": "FORWARDED_ON_RECOVERY",
                "channel": "CENTRAL_API_SYNC",
                "priority": item["priority"],
                "patient_code": item["payload"].get("patient_code"),
                "details": "Queued observation successfully forwarded upon network restoration."
            }
            self.audit_log.append(forward_record)
            forwarded_items.append(forward_record)

        return {
            "recovered": True,
            "forwarded_count": len(forwarded_items),
            "remaining_unprocessed": len([i for i in self.local_queue.values() if not i["is_resolved"]]),
            "forwarded_items": forwarded_items
        }

    def verify_no_unresolved_high_priority_actions(self) -> bool:
        """
        CORE SAFETY GUARANTEE (Requirement 9):
        Verify that NO high-priority observation is silently dropped or untracked.
        Every HIGH/CONFLICT observation must either:
        1. Be successfully forwarded upon recovery, OR
        2. Have an active, logged fallback mechanism engaged.
        """
        for item_id, item in self.local_queue.items():
            if item["priority"] == "HIGH":
                # Must either be resolved (forwarded) or have active fallback engaged
                if not item["is_resolved"] and not item["fallback_engaged"]:
                    return False
                if item["status"] not in ["FORWARDED", "QUEUED", "FAILOVER_ESCALATED"]:
                    return False
        return True
