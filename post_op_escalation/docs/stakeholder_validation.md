# User / Stakeholder Validation Summary

> **Methodology Notice:** In strict accordance with responsible AI guidelines, this section represents a **Validation Plan / Simulated Stakeholder Review**. It documents the simulated user workflow review, synthetic scenario walk-throughs, and design modifications made based on persona feedback. No claims of unverified clinical trials or actual patient human-subject interviews are made.

---

## 1. Intended Users & Stakeholder Personas

1. **Post-Operative Patients (Recovering at Home / Ward):**
   - *Needs:* Simple, stress-free self-reporting interface; immediate reassurance and clear feedback on whether to seek urgent care.
2. **Surgical Ward Nurses & Triage Staff:**
   - *Needs:* Rapid filtering of incoming patient reports; immediate alerts for deteriorating patients; transparent, non-black-box explanations.
3. **Attending Surgeons / Clinicians:**
   - *Needs:* Defensible, deterministic decision-support recommendations; assurance that no high-risk cases are dropped; full clinical autonomy.
4. **Hospital Clinical IT & Telemetry Engineers:**
   - *Needs:* Fault-tolerant store-and-forward architecture; clear separation between application logic and database persistence; automated CI/CD validation.

---

## 2. Reviewed Workflows & Validated Aspects

| Persona / Stakeholder | Workflow Reviewed | Validated Aspects | Simulated Feedback Summary | Iterative System Refinements Made |
| :--- | :--- | :--- | :--- | :--- |
| **Patient Persona** | Self-reporting vitals via web portal (`/patient`) | Clarity of numeric scale, ease of describing qualitative symptoms, understanding safety disclaimers. | *Feedback:* Entering pain as 0 while verbally complaining of agony could confuse staff. | **Implemented normalized conflict detection** to flag discordance between text reports and numeric sliders. |
| **Clinical Triage Nurse** | Live dashboard monitoring (`/clinician`) | Visual urgency badging, readability of clinical rationale, escalation lifecycle tracking (`OPEN` $\to$ `IN_PROGRESS` $\to$ `RESOLVED`). | *Feedback:* Alarm fatigue occurs if low-grade fever ($37.8^\circ\text{C}$) triggers emergency alarms. | **Tuned threshold:** Assigned low-grade temp to `MEDIUM` (4–6h re-assessment) while reserving `HIGH` auto-escalations for $\ge 38.5^\circ\text{C}$. |
| **Attending Surgeon** | Clinical review & case resolution | Deterministic rule transparency; explanation auditability; human authority retention. | *Feedback:* System must never attempt autonomous diagnosis or prescription. | **Enforced strict non-diagnostic recommendation text:** recommendations direct physical assessment by clinicians. |
| **Telemetry Engineer** | Sensor stream ingestion & network dropouts | Hardware sensor detachment, erratic Bluetooth noise, network disconnection. | *Feedback:* A noisy sensor reading showing 45°C could be ignored if code only checks normal sensor status. | **Implemented Noisy Sensor Safety Invariant:** Extreme temperature breaches on noisy channels trigger `HIGH` severity. Implemented **Store-and-Forward** queue. |

---

## 3. Human-in-the-Loop Safeguards & Remaining Concerns

1. **Human Clinician as Final Authority:**
   - The prototype operates strictly as a decision-support assistant. All auto-escalations must be accepted, managed, and marked resolved by human medical staff.
2. **Remaining Concerns & Known Limitations:**
   - **Subjective Self-Reporting Bias:** Patients may under-report or over-report pain scores based on individual anxiety or pain tolerance.
   - **Hardware Drift:** Inexpensive wearable temperature patches experience skin thermal resistance and battery fluctuations.
   - **Need for Prospective In-Vivo Validation:** Real-world hospital deployment requires rigorous IRB-approved clinical studies before clinical adoption.
