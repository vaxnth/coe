// ==========================================================================
// Clinician Decision Support Dashboard Logic - BioRecovery Platform
// Preserves exact REST API integration with FastAPI and PostgreSQL
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  let allAssessments = [];
  let allPatients = [];
  let currentRiskFilter = "ALL";
  let currentSort = "time_desc";
  let searchQuery = "";

  // Summary Metrics Elements
  const countPatients = document.getElementById("countPatients");
  const countTotal = document.getElementById("countTotal");
  const countLow = document.getElementById("countLow");
  const countMed = document.getElementById("countMed");
  const countHigh = document.getElementById("countHigh");
  const countConflict = document.getElementById("countConflict");
  const countEscalations = document.getElementById("countEscalations");

  // Progress Bar Elements
  const barFillLow = document.getElementById("barFillLow");
  const barFillMed = document.getElementById("barFillMed");
  const barFillHigh = document.getElementById("barFillHigh");
  const barFillConflict = document.getElementById("barFillConflict");
  const pctLow = document.getElementById("pctLow");
  const pctMed = document.getElementById("pctMed");
  const pctHigh = document.getElementById("pctHigh");
  const pctConflict = document.getElementById("pctConflict");

  // Sidebar Counts
  const sidebarPatientCount = document.getElementById("sidebarPatientCount");
  const sidebarObsCount = document.getElementById("sidebarObsCount");
  const sidebarEscCount = document.getElementById("sidebarEscCount");

  // Table & Toolbar Elements
  const tableBody = document.getElementById("tableBody");
  const filterBtns = document.querySelectorAll(".chip-btn[data-risk]");
  const sortSelect = document.getElementById("sortSelect");
  const searchInput = document.getElementById("searchInput");
  const refreshBtn = document.getElementById("refreshBtn");
  const liveTimestamp = document.getElementById("liveTimestamp");

  // Sidebar Navigation Buttons
  const sidebarBtns = document.querySelectorAll(".nav-item-btn[data-view]");

  // Modal Elements
  const modalOverlay = document.getElementById("escalationModal");
  const modalCloseBtn = document.getElementById("modalCloseBtn");
  const modalCancelBtn = document.getElementById("modalCancelBtn");
  const modalSaveBtn = document.getElementById("modalSaveBtn");
  const escalationForm = document.getElementById("escalationForm");
  const modalEscalationId = document.getElementById("modalEscalationId");
  const modalPatientInfo = document.getElementById("modalPatientInfo");
  const escalationStatusSelect = document.getElementById("escalationStatusSelect");
  const assignedStaffInput = document.getElementById("assignedStaffInput");
  const dueDateInput = document.getElementById("dueDateInput");

  // Live Clock
  function updateClock() {
    const now = new Date();
    liveTimestamp.textContent = now.toLocaleDateString(undefined, {
      month: "short", day: "numeric"
    }) + " • " + now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  setInterval(updateClock, 1000);
  updateClock();

  // 1. Fetch Real Data from FastAPI
  async function loadDashboardData() {
    try {
      const [assessRes, patientsRes, escRes] = await Promise.all([
        fetch("/assessments?limit=400"),
        fetch("/patients?limit=100"),
        fetch("/escalations?status=OPEN")
      ]);

      if (!assessRes.ok) throw new Error("Failed to load assessments");
      allAssessments = await assessRes.json();

      if (patientsRes.ok) {
        allPatients = await patientsRes.json();
      }

      let openEscCount = 0;
      if (escRes.ok) {
        const openEscs = await escRes.json();
        openEscCount = openEscs.length;
      }

      updateMetrics(openEscCount);
      renderTable();
    } catch (err) {
      console.error(err);
      tableBody.innerHTML = `
        <tr>
          <td colspan="11" style="text-align: center; color: #ef4444; padding: 3rem;">
            Failed to connect to backend: ${err.message}
          </td>
        </tr>
      `;
    }
  }

  // 2. Compute Real Statistics
  function updateMetrics(openEscCount) {
    const total = allAssessments.length;
    countTotal.textContent = total;
    if (sidebarObsCount) sidebarObsCount.textContent = total;

    const patientCount = allPatients.length > 0 
      ? allPatients.length 
      : new Set(allAssessments.map(a => a.patient_code)).size;
    countPatients.textContent = patientCount;
    if (sidebarPatientCount) sidebarPatientCount.textContent = patientCount;

    let low = 0, med = 0, high = 0, conflict = 0;
    allAssessments.forEach((item) => {
      const r = (item.risk_level || "").toUpperCase();
      if (r === "LOW") low++;
      else if (r === "MEDIUM") med++;
      else if (r === "HIGH") high++;
      else if (r === "CONFLICT") conflict++;
    });

    countLow.textContent = low;
    countMed.textContent = med;
    countHigh.textContent = high;
    countConflict.textContent = conflict;

    countEscalations.textContent = openEscCount;
    if (sidebarEscCount) sidebarEscCount.textContent = openEscCount;

    if (total > 0) {
      const pLow = ((low / total) * 100).toFixed(1);
      const pMed = ((med / total) * 100).toFixed(1);
      const pHigh = ((high / total) * 100).toFixed(1);
      const pConflict = ((conflict / total) * 100).toFixed(1);

      pctLow.textContent = `${pLow}% (${low})`;
      barFillLow.style.width = `${pLow}%`;

      pctMed.textContent = `${pMed}% (${med})`;
      barFillMed.style.width = `${pMed}%`;

      pctHigh.textContent = `${pHigh}% (${high})`;
      barFillHigh.style.width = `${pHigh}%`;

      pctConflict.textContent = `${pConflict}% (${conflict})`;
      barFillConflict.style.width = `${pConflict}%`;
    }
  }

  // 3. Filter & Sort Rows
  function getFilteredRows() {
    let rows = [...allAssessments];

    if (currentRiskFilter === "ESCALATED_ONLY") {
      rows = rows.filter((item) => item.escalation_status != null);
    } else if (currentRiskFilter !== "ALL") {
      rows = rows.filter(
        (item) => (item.risk_level || "").toUpperCase() === currentRiskFilter
      );
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      rows = rows.filter((item) => {
        const code = (item.patient_code || "").toLowerCase();
        const symptom = (item.symptom_description || "").toLowerCase();
        const reason = (item.reason || "").toLowerCase();
        return code.includes(q) || symptom.includes(q) || reason.includes(q);
      });
    }

    rows.sort((a, b) => {
      if (currentSort === "time_desc") {
        return new Date(b.timestamp) - new Date(a.timestamp);
      } else if (currentSort === "time_asc") {
        return new Date(a.timestamp) - new Date(b.timestamp);
      } else if (currentSort === "pain_desc") {
        return b.pain_score - a.pain_score;
      } else if (currentSort === "temp_desc") {
        const tA = a.temperature != null ? a.temperature : -1;
        const tB = b.temperature != null ? b.temperature : -1;
        return tB - tA;
      } else if (currentSort === "risk_severity") {
        const score = (r) => {
          if (r === "HIGH") return 4;
          if (r === "CONFLICT") return 3;
          if (r === "MEDIUM") return 2;
          return 1;
        };
        return score(b.risk_level) - score(a.risk_level);
      }
      return 0;
    });

    return rows;
  }

  // 4. Render Table
  function renderTable() {
    const rows = getFilteredRows();

    if (rows.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="11" style="text-align: center; color: var(--text-muted); padding: 3rem;">
            No observations found matching the selected filter criteria.
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = rows
      .map((item) => {
        const risk = (item.risk_level || "LOW").toUpperCase();
        const trClass = risk === "HIGH" ? "tr-high-risk" : risk === "CONFLICT" ? "tr-conflict-risk" : "";
        const tempText = item.temperature != null ? `${item.temperature.toFixed(1)}°C` : `<span style="color:var(--text-muted)">Missing</span>`;
        const timeStr = new Date(item.timestamp).toLocaleString(undefined, {
          month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
        });

        const painNum = item.pain_score;
        const painColor = painNum >= 7 ? "#dc2626" : painNum >= 4 ? "#d97706" : "#059669";

        let statusDisplay = `<span style="font-size:0.75rem; color:var(--text-muted)">Routine</span>`;
        let actionBtn = "";

        if (item.escalation_status) {
          const escStatus = item.escalation_status.toUpperCase();
          const badgeClass = escStatus === "OPEN" ? "status-open" : escStatus === "IN_PROGRESS" ? "status-prog" : "status-res";
          const bg = escStatus === "OPEN" ? "#fef2f2" : escStatus === "IN_PROGRESS" ? "#fffbeb" : "#ecfdf5";
          const border = escStatus === "OPEN" ? "#fecdd3" : escStatus === "IN_PROGRESS" ? "#fde68a" : "#a7f3d0";
          const color = escStatus === "OPEN" ? "#b91c1c" : escStatus === "IN_PROGRESS" ? "#b45309" : "#047857";

          statusDisplay = `
            <span style="display:inline-block; padding:0.2rem 0.6rem; border-radius:9999px; font-size:0.7rem; font-weight:700; background:${bg}; border:1px solid ${border}; color:${color};">
              ${escStatus}
            </span>
            ${item.assigned_staff ? `<div style="font-size:0.72rem; color:var(--teal-primary); font-weight:600; margin-top:2px;">👤 ${item.assigned_staff}</div>` : ""}
          `;
          actionBtn = `
            <button class="chip-btn" style="background:#ffffff; color:var(--teal-primary); border-color:var(--teal-primary);" onclick="window.openEscalationModal(${item.escalation_id})">
              Manage
            </button>
          `;
        } else if (risk === "HIGH" || risk === "CONFLICT") {
          statusDisplay = `<span style="color:#dc2626; font-size:0.75rem; font-weight:700;">Flagged</span>`;
          actionBtn = `
            <button class="chip-btn" style="border-color:#dc2626; color:#dc2626;" onclick="window.createEscalationRecord(${item.patient_id}, ${item.observation_id}, '${risk}')">
              + Escalate
            </button>
          `;
        }

        return `
          <tr class="${trClass}">
            <td>
              <strong style="color:var(--text-primary);">${item.patient_code}</strong>
            </td>
            <td style="white-space: nowrap; font-size: 0.78rem; color: var(--text-muted);">${timeStr}</td>
            <td><strong>${tempText}</strong></td>
            <td><strong style="color: ${painColor};">${painNum}</strong> / 10</td>
            <td>${item.wound_status}</td>
            <td><span style="font-size: 0.78rem; color: var(--text-muted);">${item.sensor_status}</span></td>
            <td><span class="risk-pill-badge ${risk}">${risk}</span></td>
            <td style="max-width: 240px; font-size: 0.8rem; line-height: 1.4;">${item.reason}</td>
            <td style="max-width: 220px; font-size: 0.8rem; color: var(--teal-dark); line-height: 1.4;">${item.recommendation}</td>
            <td>${statusDisplay}</td>
            <td>${actionBtn}</td>
          </tr>
        `;
      })
      .join("");
  }

  // 5. Filter Chips Click Handler
  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentRiskFilter = btn.getAttribute("data-risk");
      renderTable();
    });
  });

  // 6. Search & Sort
  searchInput.addEventListener("input", (e) => {
    searchQuery = e.target.value;
    renderTable();
  });

  sortSelect.addEventListener("change", (e) => {
    currentSort = e.target.value;
    renderTable();
  });

  refreshBtn.addEventListener("click", () => {
    loadDashboardData();
  });

  // 7. Sidebar Navigation
  sidebarBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      sidebarBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const view = btn.getAttribute("data-view");

      if (view === "escalations") {
        currentRiskFilter = "ESCALATED_ONLY";
        highlightChip("ESCALATED_ONLY");
      } else if (view === "risks") {
        currentRiskFilter = "HIGH";
        highlightChip("HIGH");
      } else if (view === "followups") {
        currentRiskFilter = "ESCALATED_ONLY";
        highlightChip("ESCALATED_ONLY");
      } else {
        currentRiskFilter = "ALL";
        highlightChip("ALL");
      }
      renderTable();
    });
  });

  function highlightChip(tag) {
    filterBtns.forEach((b) => {
      if (b.getAttribute("data-risk") === tag) {
        b.classList.add("active");
      } else {
        b.classList.remove("active");
      }
    });
  }

  // 8. Follow-up Modal Operations
  window.openEscalationModal = async function (escalationId) {
    try {
      const res = await fetch(`/escalations/${escalationId}`);
      if (!res.ok) throw new Error("Could not load escalation details");
      const esc = await res.json();

      modalEscalationId.value = esc.id;
      modalPatientInfo.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
          <span><strong>Patient:</strong> ${esc.patient_code || "ID #" + esc.patient_id}</span>
          <span><strong>Case ID:</strong> #${esc.id}</span>
        </div>
        <div style="margin-bottom: 6px;">
          <strong>Risk Level:</strong> <span class="risk-pill-badge ${esc.risk_level}">${esc.risk_level}</span>
        </div>
        <div style="margin-bottom: 6px; color: var(--text-secondary);">
          <strong>Triage Findings:</strong> ${esc.reason}
        </div>
        <div style="color: var(--teal-dark);">
          <strong>Action:</strong> ${esc.recommendation}
        </div>
      `;

      escalationStatusSelect.value = esc.status || "OPEN";
      assignedStaffInput.value = esc.assigned_staff || "";

      if (esc.due_date) {
        const d = new Date(esc.due_date);
        dueDateInput.value = d.toISOString().slice(0, 16);
      } else {
        dueDateInput.value = "";
      }

      modalOverlay.classList.add("active");
    } catch (err) {
      alert("Modal Error: " + err.message);
    }
  };

  window.createEscalationRecord = async function (patientId, observationId, riskLevel) {
    try {
      const res = await fetch("/escalations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: patientId,
          observation_id: observationId,
          risk_level: riskLevel,
          reason: "Clinician priority dispatch",
          recommendation: "Clinical evaluation and follow-up physical examination required.",
          status: "OPEN"
        })
      });
      if (!res.ok) throw new Error("Failed to create escalation");
      await loadDashboardData();
    } catch (err) {
      alert("Escalation error: " + err.message);
    }
  };

  function closeModal() {
    modalOverlay.classList.remove("active");
  }

  modalCloseBtn.addEventListener("click", closeModal);
  modalCancelBtn.addEventListener("click", closeModal);
  modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) closeModal();
  });

  // Modal Save Handler
  escalationForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const escId = modalEscalationId.value;
    const statusVal = escalationStatusSelect.value;
    const staffVal = assignedStaffInput.value.trim();
    const dueVal = dueDateInput.value ? new Date(dueDateInput.value).toISOString() : null;

    modalSaveBtn.disabled = true;
    modalSaveBtn.textContent = "Saving to Database...";

    try {
      // 1. Update Status
      await fetch(`/escalations/${escId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: statusVal })
      });

      // 2. Assign Staff
      if (staffVal) {
        await fetch(`/escalations/${escId}/assign`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ assigned_staff: staffVal })
        });
      }

      // 3. Update Due Date
      if (dueVal) {
        await fetch(`/escalations/${escId}/due-date`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ due_date: dueVal })
        });
      }

      closeModal();
      await loadDashboardData();
    } catch (err) {
      alert("Failed to save follow-up: " + err.message);
    } finally {
      modalSaveBtn.disabled = false;
      modalSaveBtn.textContent = "Save Follow-Up";
    }
  });

  // Initial Load
  loadDashboardData();
});
