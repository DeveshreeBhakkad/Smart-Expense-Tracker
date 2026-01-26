
const form = document.getElementById("uploadForm"); 
const statusMessage = document.getElementById("statusMessage");
const insightsSection = document.getElementById("insights");
const monthlyContainer = document.getElementById("monthlyContainer");

form.addEventListener("submit", async (e) => {
    e.preventDefault(); // STOP page reload

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

        if (data.error) {
            statusMessage.textContent = data.error;
            statusMessage.className = "status error";
            return;
        }

        // ✅ Reveal insights
        insightsSection.classList.remove("hidden");

        // ✅ Fill primary insight
        document.getElementById("totalExpense").textContent = `₹ ${data.total_expense}`;

        // ✅ Supporting context
        document.getElementById("totalDebit").textContent = `₹ ${data.total_debit}`;
        document.getElementById("totalCredit").textContent = `₹ ${data.total_credit}`;
        document.getElementById("topCategory").textContent = data.top_category;

        // ✅ Monthly story
        monthlyContainer.innerHTML = "";

        Object.keys(data.monthly_expense).forEach(month => {
            const monthDiv = document.createElement("div");
            monthDiv.className = "month";

            const title = document.createElement("div");
            title.className = "month-title";
            title.textContent = `${month} — ₹ ${data.monthly_expense[month]}`;

            const details = document.createElement("div");
            details.className = "month-details";
            details.style.display = "none";

            Object.entries(data.monthly_category[month]).forEach(([cat, amt]) => {
                const p = document.createElement("p");
                p.textContent = `${cat} · ₹ ${amt}`;
                details.appendChild(p);
            });

            title.onclick = () => {
                details.style.display = details.style.display === "none" ? "block" : "none";
            };

            monthDiv.appendChild(title);
            monthDiv.appendChild(details);
            monthlyContainer.appendChild(monthDiv);
        });

        statusMessage.textContent = "Statement processed successfully.";
        statusMessage.className = "status success";

    } catch (err) {
        statusMessage.textContent = "Server error. Please try again.";
        statusMessage.className = "status error";
    } finally {
        button.disabled = false;
        button.textContent = "Upload Statement";
    }
});