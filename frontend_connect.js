/**
 * Drop this into your existing frontend HTML
 * Replace your current "Analyze Emotion" button handler with this.
 *
 * The backend returns:
 * {
 *   emotion:    "happy",
 *   confidence: 91.3,
 *   emoji:      "😊",
 *   all_scores: { angry: 1.2, calm: 2.1, happy: 91.3, ... }
 * }
 */

const BACKEND_URL = "http://localhost:5000/analyze";

async function analyzeEmotion() {
  const fileInput = document.getElementById("audioFile");

  // Validate
  if (!fileInput || !fileInput.files[0]) {
    showError("Please upload a .wav file first.");
    return;
  }

  showLoading(true);
  clearError();
  clearResult();

  const formData = new FormData();
  formData.append("audio", fileInput.files[0]);

  try {
    const response = await fetch(BACKEND_URL, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Server error. Is the backend running?");
    }

    // Display main result
    displayResult(data.emotion, data.confidence, data.emoji);

    // Optionally display all scores as a breakdown bar chart
    displayAllScores(data.all_scores);

  } catch (err) {
    if (err.message.includes("fetch")) {
      showError("Cannot reach backend. Make sure 'python app.py' is running on port 5000.");
    } else {
      showError(err.message);
    }
  } finally {
    showLoading(false);
  }
}

// ---- UI helpers (adapt to your existing HTML) ----

function showLoading(state) {
  const btn = document.getElementById("analyzeBtn");
  if (btn) btn.textContent = state ? "Analyzing..." : "Analyze Emotion";
  const loader = document.getElementById("loader");
  if (loader) loader.style.display = state ? "block" : "none";
}

function showError(msg) {
  const el = document.getElementById("errorMsg");
  if (el) { el.textContent = msg; el.style.display = "block"; }
}

function clearError() {
  const el = document.getElementById("errorMsg");
  if (el) { el.textContent = ""; el.style.display = "none"; }
}

function clearResult() {
  const el = document.getElementById("resultBox");
  if (el) el.style.display = "none";
}

function displayResult(emotion, confidence, emoji) {
  // Capitalise first letter
  const label = emotion.charAt(0).toUpperCase() + emotion.slice(1);

  document.getElementById("detectedEmotion").textContent = `${emoji} ${label}`;
  document.getElementById("confidenceScore").textContent = `${confidence}% confidence`;

  const resultBox = document.getElementById("resultBox");
  if (resultBox) resultBox.style.display = "block";
}

function displayAllScores(allScores) {
  const container = document.getElementById("allScores");
  if (!container) return;

  container.innerHTML = "";

  // Sort by score descending
  const sorted = Object.entries(allScores).sort((a, b) => b[1] - a[1]);

  sorted.forEach(([emotion, score]) => {
    const label = emotion.charAt(0).toUpperCase() + emotion.slice(1);
    const row = document.createElement("div");
    row.style.cssText = "margin: 6px 0; font-size: 13px;";
    row.innerHTML = `
      <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
        <span>${label}</span>
        <span>${score}%</span>
      </div>
      <div style="background:#e0e0e0; border-radius:4px; height:6px;">
        <div style="background:#6c63ff; width:${score}%; height:100%; border-radius:4px; transition:width 0.4s;"></div>
      </div>`;
    container.appendChild(row);
  });

  container.style.display = "block";
}
