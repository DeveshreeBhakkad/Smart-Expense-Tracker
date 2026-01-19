const form = document.getElementById("uploadForm");
const statusMsg = document.getElementById("statusMessage");
const monthlyBox = document.getElementById("monthlyContainer");

form.addEventListener("submit", async e => {
    e.preventDefault();

    const file = document.querySelector("input[type=file]").files[0];
    const btn = document.getElementById("uploadBtn");

    btn.disabled = true;
    btn.innerText = "Processing...";
    statusMsg.innerText = "";

    const fd = new FormData();
    fd.append("file", file);

    try {
        const res = await fetch("/upload", { method: "POST", body: fd });
        const data = await res.json();

        if (data.error) {
            statusMsg.innerText = data.error;
            statusMsg.className = "status error";
            return;
        }

        document.getElementById("totalExpense").innerText = "₹ " + data.total_expense;
        document.getElementById("totalDebit").innerText = "₹ " + data.total_debit;
        document.getElementById("totalCredit").innerText = "₹ " + data.total_credit;
        document.getElementById("topCategory").innerText = data.top_category;

        monthlyBox.innerHTML = "";

        Object.keys(data.monthly_expense).sort().forEach(month => {
            const m = document.createElement("div");
            m.className = "month";
            m.innerText = `▼ ${month} : ₹ ${data.monthly_expense[month]}`;

            const details = document.createElement("div");
            details.className = "month-details";
            details.style.display = "none";

            Object.entries(data.monthly_category[month]).forEach(([cat, amt]) => {
                const p = document.createElement("p");
                p.innerText = `${cat}: ₹ ${amt}`;
                details.appendChild(p);
            });

            m.onclick = () => {
                details.style.display = details.style.display === "none" ? "block" : "none";
            };

            monthlyBox.appendChild(m);
            monthlyBox.appendChild(details);
        });

        statusMsg.innerText = "Statement processed successfully.";
        statusMsg.className = "status success";

    } catch {
        statusMsg.innerText = "Server error.";
        statusMsg.className = "status error";
    } finally {
        btn.disabled = false;
        btn.innerText = "Upload & Process";
    }
});

/* ---------- RESET ---------- */
document.getElementById("resetBtn").onclick = () => {
    document.getElementById("totalExpense").innerText = "₹ —";
    document.getElementById("totalDebit").innerText = "₹ —";
    document.getElementById("totalCredit").innerText = "₹ —";
    document.getElementById("topCategory").innerText = "—";
    monthlyBox.innerHTML = "<p class='muted'>No data yet</p>";
    statusMsg.innerText = "CSV cleared.";
};
