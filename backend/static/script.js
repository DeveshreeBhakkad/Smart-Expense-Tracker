document.getElementById("uploadForm").addEventListener("submit", async e => {
  e.preventDefault();

  const file = document.querySelector("input[type=file]").files[0];
  const btn = document.getElementById("uploadBtn");
  const status = document.getElementById("statusMessage");
  const monthlyBox = document.getElementById("monthlyContainer");

  status.innerText = "";
  btn.disabled = true;
  btn.innerText = "Processing...";

  const fd = new FormData();
  fd.append("file", file);

  try {
    const res = await fetch("/upload", { method: "POST", body: fd });
    const data = await res.json();

    if (data.error) {
      status.innerText = data.error;
      status.className = "status error";
      return;
    }

    document.getElementById("totalExpense").innerText = "₹ " + data.total_expense;
    document.getElementById("totalDebit").innerText = "₹ " + data.total_debit;
    document.getElementById("totalCredit").innerText = "₹ " + data.total_credit;
    document.getElementById("topCategory").innerText = data.top_category;

    monthlyBox.innerHTML = "";

    Object.keys(data.monthly_expense).sort().forEach(month => {
      const div = document.createElement("div");
      div.innerHTML = `▼ ${month} : ₹ ${data.monthly_expense[month]}`;
      div.style.cursor = "pointer";

      const details = document.createElement("ul");
      details.style.display = "none";

      Object.entries(data.monthly_category[month]).forEach(([cat, amt]) => {
        const li = document.createElement("li");
        li.innerText = `${cat}: ₹ ${amt}`;
        details.appendChild(li);
      });

      div.onclick = () => {
        details.style.display = details.style.display === "none" ? "block" : "none";
      };

      monthlyBox.appendChild(div);
      monthlyBox.appendChild(details);
    });

    status.innerText = "Statement processed successfully.";
    status.className = "status success";

  } catch {
    status.innerText = "Server error.";
    status.className = "status error";
  } finally {
    btn.disabled = false;
    btn.innerText = "Upload & Process";
  }
});
