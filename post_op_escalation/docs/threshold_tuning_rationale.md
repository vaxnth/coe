# Clinical & Telemetry Threshold-Tuning Rationale

This document presents the detailed clinical rationale, simulation validation context, and boundary sensitivity analysis for all vital signs, pain indicators, and telemetry quality cut-offs utilized by the rule engine.

---

## 1. Summary Threshold Specification Matrix

| Vital Signal | Threshold / Cut-Off | Clinical Risk Tier | Medical & Engineering Rationale | Internal Simulation Validation | Boundary Behavior & Sensitivity | Clinical Limitations & Real-World Validation Requirements |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Severe Pyrexia / Fever** | $\ge 38.5^\circ\text{C}$ ($101.3^\circ\text{F}$) | `HIGH` | Indicates potential acute surgical site infection (SSI), deep fascial infection, pneumonia, or systemic inflammatory response. | Tested against simulated febrile cases; consistently triggers prompt triage notification and escalation. | Values at $38.4^\circ\text{C}$ enter `MEDIUM` risk, requiring reassessment within 4–6h. No sudden drop to `LOW`. | Real-world physiological variation occurs due to antipyretics (e.g., acetaminophen), diurnal rhythm, and ambient sensor thermal drift. Prospective trial required. |
| **Severe Hypothermia** | $< 35.0^\circ\text{C}$ ($95.0^\circ\text{F}$) | `HIGH` | Post-operative hypothermia correlates with impaired platelet function, coagulopathy, delayed wound healing, or hemodynamic shock. | Verified across boundary test cases ($34.9^\circ\text{C}$); flags immediate critical review. | Values at $35.0^\circ\text{C} - 35.9^\circ\text{C}$ transition to `MEDIUM` alert for active re-warming monitoring. | Sensor detachment can mimic ambient room cooling. Requires cross-verification with physical skin contact sensors. |
| **Mild / Low-Grade Temperature Elevation** | $37.5^\circ\text{C} - 38.4^\circ\text{C}$ | `MEDIUM` | Typical benign early post-operative inflammatory response (cytokine release post-tissue trauma) during initial 24–48 hours. | Simulated across 30 medium-risk patient cases without triggering unnecessary alarm fatigue. | If accompanied by qualitative chills or rigors, conflict engine elevates priority to `CONFLICT`. | Cannot distinguish benign atelectasis from early evolving bacteremia without laboratory biomarkers (WBC, CRP). |
| **Severe Post-Operative Pain** | $\ge 7 / 10$ (or qualitative severe descriptions) | `HIGH` | Breakthrough pain disproportionate to expected recovery indicates surgical complications: wound dehiscence, hematoma tension, compartment pressure, or ischemia. | Validated in automated edge-case test suite (`test_conflict_and_severity.py`). | Score $6/10$ remains `MEDIUM`. Score $7/10$ transitions immediately to `HIGH` auto-escalation. | Numeric rating is subjective; patient pain tolerance, psychological distress, and baseline opioid tolerance vary widely. |
| **Moderate Pain** | $4 - 6 / 10$ | `MEDIUM` | Common expected post-operative discomfort managed with scheduled oral analgesics. | Evaluated across ambulatory recovery profiles; prompts routine follow-up within 4–6h. | Score $3/10$ transitions to `LOW` baseline recovery. | Requires nursing assessment to adjust medication intervals. |
| **Critical Wound Condition** | `Discharge`, `Bleeding` (or purulent text) | `HIGH` | Active bloody pooling suggests vascular hemorrhage or suture disruption; purulent discharge is definitive physical indicator of surgical site infection. | Fully tested in rules engine; triggers auto-escalation regardless of sensor status. | Discrete status entry. Supported by free-text semantic extraction (`purulent`, `pus`, `oozing`). | Subjective self-assessment by patients may mistake serosanguinous fluid for active bleeding. Requires clinical photo or in-person check. |
| **Wound Erythema & Edema** | `Redness`, `Swelling` | `MEDIUM` | Localized inflammatory perimeter changes requiring monitoring for spreading margins (cellulitis). | Verified in synthetic dataset; categorized into `MEDIUM` risk. | Combined with fever or high pain, elevates case to `HIGH`. | Perimeter measurement is qualitative; digital wound planimetry would be required in hospital settings. |
| **Noisy Sensor Reading** | Erratic telemetry spikes ($\ge 42^\circ\text{C}$ or $< 32^\circ\text{C}$) | `MEDIUM` (or `HIGH` on critical vital breach) | **Safety-First Guarantee:** A reading indicating extreme physiology must never be ignored solely because sensor telemetry is tagged noisy. | Tested in `test_noisy_reading_cannot_bypass_critical_temperature`. | If reading breaches high thresholds, triggers `HIGH` severity with explicit data quality notice. | Signal-to-noise ratio in low-cost BLE sensors requires physical lead inspection. |
| **Missing Sensor Data** | `temperature is None` / `np.nan` | `MEDIUM` | Lost telemetry stream prevents continuous safety monitoring; requires patch re-attachment or manual vitals. | Tested with simulated disconnected telemetry (`Missing`). | If pain or wound is severe, overall risk escalates to `HIGH` based on intact clinical reports. | System gracefully functions as self-report portal during telemetry hardware downtime. |

---

## 2. Distinction Between Project Validation and Clinical Validation

- **Validated Within Project:**
  - Mathematical correctness of boundary evaluation ($34.9$ vs $35.0$, $38.4$ vs $38.5$).
  - Deterministic reproducibility using fixed random seeds.
  - Absence of silent bypasses during noisy or missing telemetry streams.
  - Zero dropped high-priority actions across network outages.

- **Mandatory Clinical Validation Still Required for Real-World Use:**
  - Prospective multi-center clinical trials evaluating sensitivity and specificity against surgical gold standards.
  - Institutional Review Board (IRB) ethical approval.
  - Calibration across specific patient sub-populations (e.g., pediatric, geriatric, immunosuppressed, or cardiac surgery cohorts).
  - Formal regulatory clearance (e.g., FDA SaMD or CE mark Class IIb) as a clinical decision support system.
