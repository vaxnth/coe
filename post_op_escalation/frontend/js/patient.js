// ==========================================================================
// Patient Portal Frontend Logic - Apple Health & Mobile Health 3D Style
// Preserves exact REST API integration with FastAPI and PostgreSQL
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  // Greeting Header
  const dynamicGreeting = document.getElementById("dynamicGreeting");
  const hour = new Date().getHours();
  if (dynamicGreeting) {
    if (hour < 12) dynamicGreeting.textContent = "Good Morning";
    else if (hour < 17) dynamicGreeting.textContent = "Good Afternoon";
    else dynamicGreeting.textContent = "Good Evening";
  }

  // Inputs
  const patientCodeInput = document.getElementById("patientCode");
  const painSlider = document.getElementById("painScore");
  const painDisplay = document.getElementById("painValueDisplay");
  const painDescriptor = document.getElementById("painDescriptor");
  const sensorSelect = document.getElementById("sensorStatus");
  const tempInput = document.getElementById("temperature");
  const woundSelect = document.getElementById("woundStatus");
  const symptomTextarea = document.getElementById("symptomDescription");
  const form = document.getElementById("observationForm");
  const submitBtn = document.getElementById("submitBtn");

  // Health Metric Cards (Apple Health style)
  const cardValPain = document.getElementById("cardValPain");
  const cardStatusPain = document.getElementById("cardStatusPain");
  const cardValTemp = document.getElementById("cardValTemp");
  const cardStatusTemp = document.getElementById("cardStatusTemp");
  const cardValWound = document.getElementById("cardValWound");
  const cardStatusWound = document.getElementById("cardStatusWound");
  const cardValRisk = document.getElementById("cardValRisk");
  const heroRiskBadge = document.getElementById("heroRiskBadge");
  const cardValSensor = document.getElementById("cardValSensor");
  const cardValEsc = document.getElementById("cardValEsc");

  // Floating 3D Telemetry Nodes
  const floatTempVal = document.getElementById("floatTempVal");
  const floatPainVal = document.getElementById("floatPainVal");
  const floatWoundVal = document.getElementById("floatWoundVal");
  const floatSensorVal = document.getElementById("floatSensorVal");
  const woundNode = document.getElementById("woundNode");

  // Assessment Result Elements
  const resultCard = document.getElementById("resultCard");
  const riskBadge = document.getElementById("riskBadge");
  const resultReason = document.getElementById("resultReason");
  const resultRecommendation = document.getElementById("resultRecommendation");
  const escalationNotice = document.getElementById("escalationNotice");

  // 1. Pain Slider Synchronization
  function updatePain(val) {
    const num = parseInt(val, 10);
    painDisplay.textContent = num;
    if (cardValPain) cardValPain.innerHTML = `${num} <span style="font-size: 1.1rem; color: var(--text-muted);">/ 10</span>`;
    if (floatPainVal) floatPainVal.textContent = `Pain: ${num}/10`;

    if (num === 0) {
      painDescriptor.textContent = "No Pain (0)";
      painDisplay.style.background = "var(--risk-low-color)";
      if (cardStatusPain) cardStatusPain.textContent = "Zero discomfort";
    } else if (num <= 3) {
      painDescriptor.textContent = "Mild Pain (1-3)";
      painDisplay.style.background = "var(--teal-primary)";
      if (cardStatusPain) cardStatusPain.textContent = "Mild • Well-tolerated";
    } else if (num <= 6) {
      painDescriptor.textContent = "Moderate Pain (4-6)";
      painDisplay.style.background = "var(--risk-med-color)";
      if (cardStatusPain) cardStatusPain.textContent = "Moderate soreness noted";
    } else {
      painDescriptor.textContent = "Severe Pain (7-10)";
      painDisplay.style.background = "var(--risk-high-color)";
      if (cardStatusPain) cardStatusPain.textContent = "Severe / Acute discomfort";
    }
  }

  painSlider.addEventListener("input", (e) => updatePain(e.target.value));
  updatePain(painSlider.value);

  // 2. Temperature Input Synchronization
  function updateTemp() {
    if (sensorSelect.value === "Missing" || !tempInput.value) {
      if (floatTempVal) floatTempVal.textContent = "Temp: N/A";
      if (cardValTemp) cardValTemp.innerHTML = `N/A`;
      if (cardStatusTemp) cardStatusTemp.textContent = "Sensor missing / offline";
    } else {
      const val = parseFloat(tempInput.value);
      const formatted = isNaN(val) ? "--" : `${val.toFixed(1)} °C`;
      if (floatTempVal) floatTempVal.textContent = isNaN(val) ? "--" : `${val.toFixed(1)}°C`;
      if (cardValTemp) cardValTemp.innerHTML = isNaN(val) ? "--" : `${val.toFixed(1)} <span style="font-size: 1.1rem; color: var(--text-muted);">°C</span>`;

      if (val >= 38.5) {
        if (cardStatusTemp) cardStatusTemp.textContent = "High fever recorded";
      } else if (val >= 37.5) {
        if (cardStatusTemp) cardStatusTemp.textContent = "Low-grade warmth";
      } else {
        if (cardStatusTemp) cardStatusTemp.textContent = "Normal baseline recovery";
      }
    }
  }

  tempInput.addEventListener("input", updateTemp);

  // 3. Sensor Status Handler
  sensorSelect.addEventListener("change", (e) => {
    const s = e.target.value;
    if (floatSensorVal) floatSensorVal.textContent = s;
    if (cardValSensor) cardValSensor.textContent = s;

    if (s === "Missing") {
      tempInput.disabled = true;
      tempInput.value = "";
      updateTemp();
    } else if (s === "Noisy") {
      tempInput.disabled = false;
      if (!tempInput.value) tempInput.value = "37.0";
      updateTemp();
    } else {
      tempInput.disabled = false;
      if (!tempInput.value) tempInput.value = "36.9";
      updateTemp();
    }
  });

  // 4. Wound Status Handler
  woundSelect.addEventListener("change", (e) => {
    const w = e.target.value;
    if (floatWoundVal) floatWoundVal.textContent = w;
    if (cardValWound) cardValWound.textContent = w;

    if (woundNode) {
      if (w === "Bleeding" || w === "Discharge") {
        woundNode.setAttribute("fill", "#dc2626");
        if (cardStatusWound) cardStatusWound.textContent = "Active drainage / bleeding";
      } else if (w === "Redness" || w === "Swelling") {
        woundNode.setAttribute("fill", "#d97706");
        if (cardStatusWound) cardStatusWound.textContent = "Mild perimeter irritation";
      } else {
        woundNode.setAttribute("fill", "#0d9488");
        if (cardStatusWound) cardStatusWound.textContent = "Clean margins, closed";
      }
    }
  });

  // Initial Sync
  updateTemp();

  // 5. Form Submission Handler
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>⏳</span> Submitting & Analyzing...`;
    resultCard.classList.remove("active");

    const patientCode = patientCodeInput.value.trim();
    const sensorStatus = sensorSelect.value;
    const temperature = sensorStatus === "Missing" || !tempInput.value
      ? null
      : parseFloat(tempInput.value);
    const painScore = parseInt(painSlider.value, 10);
    const woundStatus = woundSelect.value;
    const symptomDescription = symptomTextarea.value.trim();

    try {
      // Step 1: POST observation to FastAPI
      const obsPayload = {
        patient_code: patientCode,
        sensor_status: sensorStatus,
        temperature: temperature,
        pain_score: painScore,
        wound_status: woundStatus,
        symptom_description: symptomDescription || null
      };

      const obsRes = await fetch("/observations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(obsPayload)
      });

      if (!obsRes.ok) {
        const err = await obsRes.json();
        throw new Error(err.detail || "Failed to submit observation");
      }

      const observation = await obsRes.json();

      // Step 2: Run existing rule engine
      const assessRes = await fetch(`/assess/${observation.id}`, {
        method: "POST"
      });

      if (!assessRes.ok) {
        const err = await assessRes.json();
        throw new Error(err.detail || "Failed to evaluate observation");
      }

      const assessment = await assessRes.json();

      // Step 3: Render Result Card
      renderResult(assessment);

    } catch (err) {
      alert("Submission Error: " + err.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>⚡</span> Submit Observation & Analyze`;
    }
  });

  function renderResult(assessment) {
    const risk = (assessment.risk_level || "LOW").toUpperCase();

    // Update Result Card
    riskBadge.textContent = risk + " RISK";
    riskBadge.className = `risk-pill-badge ${risk}`;
    resultReason.textContent = assessment.reason;
    resultRecommendation.textContent = assessment.recommendation;

    // Update Top Hero Card & Metric Cards
    if (heroRiskBadge) {
      heroRiskBadge.textContent = risk + " RISK";
      heroRiskBadge.className = `risk-pill-badge ${risk}`;
    }
    if (cardValRisk) {
      cardValRisk.textContent = risk;
      cardValRisk.style.color = risk === "HIGH" ? "#dc2626" : risk === "CONFLICT" ? "#7c3aed" : risk === "MEDIUM" ? "#d97706" : "#059669";
    }

    if (risk === "HIGH" || risk === "CONFLICT") {
      escalationNotice.style.display = "block";
      escalationNotice.innerHTML = `
        <strong>🚨 Clinical Escalation Alert:</strong> Observation flagged as <strong>${risk}</strong> risk. 
        Escalation record #${assessment.escalation_id || "NEW"} registered in clinician triage queue.
      `;
      if (cardValEsc) {
        cardValEsc.textContent = "Flagged";
        cardValEsc.style.color = "#dc2626";
      }
    } else {
      escalationNotice.style.display = "none";
      if (cardValEsc) {
        cardValEsc.textContent = "Routine";
        cardValEsc.style.color = "#059669";
      }
    }

    resultCard.classList.add("active");
    resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
});
