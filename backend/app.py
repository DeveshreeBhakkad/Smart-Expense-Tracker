from flask import Flask, request, send_file, redirect
import os
import csv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)

LAST_PDF_PATH = None


# ===============================
# HOME → REDIRECT TO UI
# ===============================
@app.route("/")
def home():
    return redirect("/upload-form")


# ===============================
# UI PAGE
# ===============================
@app.route("/upload-form")
def upload_form():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "upload.html")
    return open(html_path, encoding="utf-8").read()


# ===============================
# UPLOAD + PROCESS
# ===============================
@app.route("/upload", methods=["POST"])
def upload():
    global LAST_PDF_PATH

    if "file" not in request.files:
        return {"error": "No file uploaded"}, 400

    file = request.files["file"]

    if file.filename == "":
        return {"error": "No file selected"}, 400


    # ---------- SAVE FILE ----------
    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_folder = os.path.join(base_dir, "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, file.filename)
    file.save(file_path)


    # ---------- READ CSV ----------
    rows = []
    try:
        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rows.append(row)
    except Exception:
        return {"error": "Invalid CSV file"}, 400


    # ---------- NORMALIZE + CATEGORIZE ----------
    transactions = []

    for row in rows:
        try:
            raw_amount = float(row["Amount"])
        except Exception:
            continue  # skip bad rows

        if "Type" in row and row["Type"]:
            if row["Type"].strip().upper() in ["DR", "DEBIT"]:
                txn_type = "debit"
            else:
                txn_type = "credit"
            amount_value = raw_amount
        else:
            if raw_amount < 0:
                txn_type = "debit"
                amount_value = abs(raw_amount)
            else:
                txn_type = "credit"
                amount_value = raw_amount

        description = row.get("Description", "").lower()

        if txn_type == "credit":
            category = "Income"
        elif "swiggy" in description or "zomato" in description:
            category = "Food"
        elif "amazon" in description or "flipkart" in description:
            category = "Shopping"
        elif "uber" in description or "ola" in description:
            category = "Travel"
        elif "recharge" in description:
            category = "Utilities"
        elif "rent" in description:
            category = "Rent"
        else:
            category = "Others"

        transactions.append({
            "date": row.get("Date", ""),
            "description": row.get("Description", ""),
            "amount": amount_value,
            "type": txn_type,
            "category": category
        })

    if not transactions:
        return {"error": "No valid transactions found"}, 400


    # ---------- SUMMARY ----------
    category_summary = {}
    total_debit = 0
    total_credit = 0

    for txn in transactions:
        if txn["type"] == "debit":
            category_summary[txn["category"]] = category_summary.get(txn["category"], 0) + txn["amount"]
            total_debit += txn["amount"]
        else:
            total_credit += txn["amount"]


    # ---------- PDF GENERATION ----------
    report_folder = os.path.join(base_dir, "reports")
    os.makedirs(report_folder, exist_ok=True)

    pdf_path = os.path.join(report_folder, "expense_report.pdf")
    LAST_PDF_PATH = pdf_path

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 40

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Expense Report")
    y -= 30

    c.setFont("Helvetica", 10)
    headers = ["Date", "Description", "Amount", "Type", "Category"]
    x = [40, 120, 300, 360, 420]

    for i in range(len(headers)):
        c.drawString(x[i], y, headers[i])
    y -= 20

    for txn in transactions:
        if y < 50:
            c.showPage()
            y = height - 40

        c.drawString(40, y, txn["date"])
        c.drawString(120, y, txn["description"][:25])
        c.drawString(300, y, str(txn["amount"]))
        c.drawString(360, y, txn["type"])
        c.drawString(420, y, txn["category"])
        y -= 15

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Summary")
    y -= 20

    c.setFont("Helvetica", 10)
    for cat, amt in category_summary.items():
        c.drawString(40, y, f"{cat}: {amt}")
        y -= 15

    y -= 10
    c.drawString(40, y, f"Total Debit: {total_debit}")
    y -= 15
    c.drawString(40, y, f"Total Credit: {total_credit}")

    c.save()

    return {
        "total_debit": total_debit,
        "total_credit": total_credit,
        "category_summary": category_summary
    }


# ===============================
# DOWNLOAD PDF
# ===============================
@app.route("/download-report")
def download_report():
    if LAST_PDF_PATH and os.path.exists(LAST_PDF_PATH):
        return send_file(
            LAST_PDF_PATH,
            as_attachment=True,
            download_name="expense_report.pdf"
        )
    return {"error": "No report available"}, 404


if __name__ == "__main__":
    app.run(debug=True)
