const form = document.getElementById("uploadForm");
const statusMessage = document.getElementById("statusMessage");
const insights = document.getElementById("insights");
const monthlyContainer = document.getElementById("monthlyContainer");
const passwordBox = document.getElementById("passwordBox");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const fileInput = document.getElementById("fileInput");
    const passwordInput = document.getElementById("pdfPassword");
    const btn = document.getElementById("uploadBtn");

    if (!fileInput.files.length) {
        statusMessage.textContent = "Please select a file.";
        statusMessage.className = "status error";
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    if (passwordInput.value) {
        formData.append("password", passwordInput.value);
    }

    btn.disabled = true;
    btn.textContent = "Processing…";

    const res = await fetch("/upload", { method: "POST", body: formData });
    const data = await res.json();

    btn.disabled = false;
    btn.textContent = "Upload & Analyze";

    if (data.needs_password) {
        passwordBox.style.display = "block";
        statusMessage.textContent = "This PDF is password protected.";
        statusMessage.className = "status error";
        return;
    }

    if (data.error) {
        statusMessage.textContent = data.error;
        statusMessage.className = "status error";
        return;
    }

    insights.classList.remove("hidden");
    statusMessage.textContent = "Statement processed successfully.";
    statusMessage.className = "status success";

    document.getElementById("totalExpense").textContent = `₹ ${data.total_expense}`;
    document.getElementById("totalDebit").textContent = `₹ ${data.total_debit}`;
    document.getElementById("totalCredit").textContent = `₹ ${data.total_credit}`;
    document.getElementById("topCategory").textContent = data.top_category;

    monthlyContainer.innerHTML = "";
    Object.keys(data.monthly_expense).forEach(month => {
        const div = document.createElement("div");
        div.innerHTML = `<strong>${month}</strong> — ₹ ${data.monthly_expense[month]}`;
        monthlyContainer.appendChild(div);
    });
});
