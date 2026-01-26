
const form = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const passwordInput = document.getElementById("pdfPassword");
const statusMessage = document.getElementById("statusMessage");
const insights = document.getElementById("insights");
const totalExpense = document.getElementById("totalExpense");

let lastFile = null;

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (!fileInput.files.length && !lastFile) {
    statusMessage.textContent = "Please select a file.";
    return;
  }

  const formData = new FormData();
  const file = fileInput.files[0] || lastFile;
  lastFile = file;

  formData.append("file", file);

  if (!passwordInput.classList.contains("hidden")) {
    formData.append("password", passwordInput.value);
  }

  statusMessage.textContent = "Processing…";

  const res = await fetch("/upload", {
    method: "POST",
    body: formData
  });

  const data = await res.json();

  if (data.error === "PDF_PASSWORD_REQUIRED") {
    passwordInput.classList.remove("hidden");
    statusMessage.textContent = "PDF is password protected. Enter password.";
    return;
  }

  if (data.error) {
    statusMessage.textContent = data.error;
    return;
  }

  insights.classList.remove("hidden");
  totalExpense.textContent = "₹ " + data.total_expense;
  statusMessage.textContent = "Analysis complete.";
});
