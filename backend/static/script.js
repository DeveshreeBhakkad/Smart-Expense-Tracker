const form = document.getElementById("uploadForm");
const statusMessage = document.getElementById("statusMessage");
const insightsSection = document.getElementById("insights");
const monthlyContainer = document.getElementById("monthlyContainer");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const fileInput = form.querySelector("input[type='file']");
    const button = document.getElementById("uploadBtn");

    if (!fileInput.files.length) {
        statusMessage.textContent = "Please select a CSV file.";
        statusMessage.className = "status error";
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    button.disabled = true;
    button.textContent = "Processing…";
    statusMessage.textContent = "";

    try {
        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        if (data.error) throw new Error();

        insightsSection.classList.remove("hidden");

        document.getElementById("totalExpense").textContent = `₹ ${data.total_expense}`;
        document.getElementById("totalDebit").textContent = `₹ ${data.total_debit}`;
        document.getElementById("totalCredit").textContent = `₹ ${data.total_credit}`;
        document.getElementById("topCategory").textContent = data.top_category;

        monthlyContainer.innerHTML = "";

        Object.keys(data.monthly_expense).forEach(month => {
            const monthDiv = document.createElement("div");
            monthDiv.className = "month";

            const title = document.createElement("div");
            title.className = "month-title";
            title.textContent = `${month} — ₹ ${data.monthly_expense[month]}`;

            const details = document.createElement("div");
            details.className = "month-details";

            Object.entries(data.monthly_category[month]).forEach(([cat, amt]) => {
                const p = document.createElement("p");
                p.textContent = `${cat} · ₹ ${amt}`;
                details.appendChild(p);
            });

            title.onclick = () => {
                document.querySelectorAll(".month-details").forEach(d => d.style.display = "none");
                details.style.display = "block";
            };

            monthDiv.appendChild(title);
            monthDiv.appendChild(details);
            monthlyContainer.appendChild(monthDiv);
        });

        statusMessage.textContent = "Statement processed successfully.";
        statusMessage.className = "status success";

    } catch {
        statusMessage.textContent = "Server error.";
        statusMessage.className = "status error";
    } finally {
        button.disabled = false;
        button.textContent = "Upload & Analyze";
    }
});
