document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const fileInput = document.querySelector('input[type="file"]');
    const uploadBtn = document.getElementById("uploadBtn");
    const statusMsg = document.getElementById("statusMessage");

    statusMsg.innerText = "";
    statusMsg.className = "status";

    if (!fileInput.files.length) {
        statusMsg.innerText = "Please select a CSV file.";
        statusMsg.classList.add("error");
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    // Loading state
    uploadBtn.disabled = true;
    uploadBtn.innerText = "Processing...";

    try {
        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            statusMsg.innerText = data.error;
            statusMsg.classList.add("error");
            return;
        }

        document.getElementById("totalDebit").innerText = "₹ " + data.total_debit;
        document.getElementById("totalCredit").innerText = "₹ " + data.total_credit;

        let topCategory = "—";
        let maxAmount = 0;

        for (const cat in data.category_summary) {
            if (data.category_summary[cat] > maxAmount) {
                maxAmount = data.category_summary[cat];
                topCategory = cat;
            }
        }

        document.getElementById("topCategory").innerText = topCategory;

        statusMsg.innerText = "Statement processed successfully.";
        statusMsg.classList.add("success");

    } catch (err) {
        console.error(err);
        statusMsg.innerText = "Server error. Please try again.";
        statusMsg.classList.add("error");
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerText = "Upload & Process";
    }
});
