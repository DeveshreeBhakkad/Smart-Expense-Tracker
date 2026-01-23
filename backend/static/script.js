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

         if (data.password_required) {
              statusMessage.textContent = "This PDF is password protected. Support coming next.";
              statusMessage.className = "status error";
              return;
        }

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
            title.innerHTML = `<span>▼ ${month}</span><span>₹ ${data.monthly_expense[month]}</span>`;

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
        statusMessage.textContent = "Server error. Please try again.";
        statusMessage.className = "status error";
    } finally {
        button.disabled = false;
        button.textContent = "Upload & Analyze";
    }
});
let pdfToken = null;

document.getElementById("unlockBtn").onclick = async () => {
    const password = document.getElementById("pdfPassword").value;

    const res = await fetch("/unlock-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            file_token: pdfToken,
            password
        })
    });

    const data = await res.json();
    if (data.error) {
        alert(data.error);
        return;
    }

    document.getElementById("passwordBox").classList.add("hidden");
    renderInsights(data); // reuse your existing render logic
};
