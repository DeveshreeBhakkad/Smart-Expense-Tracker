const form = document.getElementById("uploadForm");
const statusMessage = document.getElementById("statusMessage");
const insights = document.getElementById("insights");
const monthlyContainer = document.getElementById("monthlyContainer");
const passwordInput = document.getElementById("pdfPassword");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const fileInput = form.querySelector("input[type='file']");
    const btn = document.getElementById("uploadBtn");

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    if (passwordInput.value) {
        formData.append("password", passwordInput.value);
    }

    btn.disabled = true;
    statusMessage.textContent = "Processing...";

    const res = await fetch("/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (data.password_required) {
        passwordInput.style.display = "block";
        statusMessage.textContent = "This PDF is password protected.";
        btn.disabled = false;
        return;
    }

    if (data.error) {
        statusMessage.textContent = data.error;
        btn.disabled = false;
        return;
    }

    insights.classList.remove("hidden");
    document.getElementById("totalExpense").textContent = `₹ ${data.total_expense}`;
    document.getElementById("totalDebit").textContent = `₹ ${data.total_debit}`;
    document.getElementById("totalCredit").textContent = `₹ ${data.total_credit}`;
    document.getElementById("topCategory").textContent = data.top_category;

    monthlyContainer.innerHTML = "";

    for (const m in data.monthly_expense) {
        const div = document.createElement("div");
        div.className = "month";
        div.innerHTML = `<strong>${m}</strong> — ₹ ${data.monthly_expense[m]}`;

        const details = document.createElement("div");
        for (const c in data.monthly_category[m]) {
            details.innerHTML += `<p>${c}: ₹ ${data.monthly_category[m][c]}</p>`;
        }

        div.onclick = () => details.classList.toggle("hidden");
        monthlyContainer.append(div, details);
    }

    statusMessage.textContent = "Statement processed successfully.";
    btn.disabled = false;
});
