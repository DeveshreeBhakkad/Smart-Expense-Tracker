const form = document.getElementById("uploadForm");
const statusMessage = document.getElementById("statusMessage");
const pdfPassword = document.getElementById("pdfPassword");
const analyzeAnother = document.getElementById("analyzeAnother");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const file = document.getElementById("fileInput").files[0];
  if (!file) {
    statusMessage.textContent = "Please select a file.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  if (!pdfPassword.classList.contains("hidden")) {
    formData.append("password", pdfPassword.value);
  }

  statusMessage.textContent = "Analyzing statement...";

  const res = await fetch("/upload", {
    method: "POST",
    body: formData
  });

  const json = await res.json();

  // -------- PASSWORD HANDLING --------
  if (json.error === "PASSWORD_REQUIRED") {
    pdfPassword.classList.remove("hidden");
    statusMessage.textContent = "Password required.";
    return;
  }

  if (json.error === "INCORRECT_PASSWORD") {
    pdfPassword.classList.remove("hidden");
    statusMessage.textContent = "Incorrect password. Please try again.";
    return;
  }

  if (json.error) {
    statusMessage.textContent = json.error;
    return;
  }

  // -------- SUMMARY --------
  document.getElementById("totalExpense").textContent = `₹ ${json.total_expense}`;
  document.getElementById("totalDebit").textContent = `₹ ${json.total_debit}`;
  document.getElementById("totalCredit").textContent = `₹ ${json.total_credit}`;
  document.getElementById("topCategory").textContent = json.top_category;

  // ---- Smart Insights ----
const insightEl = document.getElementById("insightLine");

let insights = [];

// Rule 1: Expense vs Income
if (json.total_debit > json.total_credit) {
  insights.push("💸 Your expenses are higher than your income.");
} else if (json.total_credit > json.total_debit) {
  insights.push("✅ You saved more than you spent.");
}

// Rule 2: Top category
if (json.top_category && json.top_category !== "—") {
  insights.push(`📊 Most spending happened on ${json.top_category}.`);
}

// Rule 3: Highest expense month
if (json.monthly_expense) {
  const entries = Object.entries(json.monthly_expense);
  if (entries.length > 0) {
    const [maxMonth] = entries.reduce((a, b) => (b[1] > a[1] ? b : a));
    insights.push(`📆 Highest spending month: ${maxMonth}.`);
  }
}

// Fallback
if (insights.length === 0) {
  insights.push("No significant spending patterns detected.");
}

// Show only 2–3 insights (clean UI)
insightEl.innerHTML = insights.join("<br>");


  // -------- DEBIT / CREDIT MINI SUMMARY --------
  document.getElementById("dcDebit").textContent = `₹ ${json.total_debit}`;
  document.getElementById("dcCredit").textContent = `₹ ${json.total_credit}`;

  // -------- MONTHLY BREAKDOWN --------
  const debitBox = document.getElementById("monthlyDebit");
  const creditBox = document.getElementById("monthlyCredit");

  debitBox.innerHTML = "";
  creditBox.innerHTML = "";

  // Debit months
  Object.entries(json.monthly_expense || {}).forEach(([month, amt]) => {
    debitBox.innerHTML += `<p>${month} — ₹ ${amt}</p>`;
  });

  // Credit months (FIXED)
  Object.entries(json.monthly_credit || {}).forEach(([month, amt]) => {
    creditBox.innerHTML += `<p>${month} — ₹ ${amt}</p>`;
  });

  statusMessage.textContent = "Analysis complete.";
  analyzeAnother.classList.remove("hidden");
});

analyzeAnother.onclick = () => window.location.reload();

// -------- DOWNLOAD REPORTS --------
document.getElementById("downloadDebit")?.addEventListener("click", () => {
  window.open("/download-report?type=debit", "_blank");
});

document.getElementById("downloadCredit")?.addEventListener("click", () => {
  window.open("/download-report?type=credit", "_blank");
});
