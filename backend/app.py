from flask import Flask, request, send_file, redirect
import os
import csv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)

LAST_PDF_PATH = None


# ===============================
# HOME → UI
# ===============================
@app.route("/")
def home():
    return redirect("/upload-form")


@app.route("/upload-form")
def upload_form():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return open(os.path.join(base_dir, "upload.html"), encoding="utf-8").read()


# ===============================
# UNIVERSAL ROW PARSER
# ===============================
def parse_transaction_row(row):
    """
    Returns (amount, txn_type) or None
    Handles:
    - Amount
    - Debit / Credit
    - Withdrawal / Deposit
    - DR / CR
    """

    def clean(value):
        return value.replace(",", "").strip()

    # 1️⃣ Debit / Credit columns
    for debit_key in ["Debit", "Withdrawal"]:
        if debit_key in row and row[debit_key].strip():
            try:
                return float(clean(row[debit_key])), "debit"
            except:
                return None

    for credit_key in ["Credit", "Deposit"]:
        if credit_key in row and row[credit_key].strip():
            try:
                return float(clean(row[credit_key])), "credit"
            except:
                return None

    # 2️⃣ Amount + Type column
    if "Amount" in row and row["Amount"].strip():
        try:
            amount = float(clean(row["Amount"]))
        except:
            return None

        txn_type = None

        for type_key in ["Type", "Dr/Cr", "DRCR"]:
            if type_key in row:
                value = row[type_key].upper()
                if "DR" in value or "DEBIT" in value:
                    txn_type = "debit"
                elif "CR" in value or "CREDIT" in value:
                    txn_type = "credit"

        if txn_type:
            return abs(amount), txn_type

        # fallback: sign based
        if amount < 0:
            return abs(amount), "debit"
        else:
            return amount, "credit"

    return None


# ===============================
# UPLOAD ROUTE
# ===============================
@app.route("/upload", methods=["POST"])
def upload():
    global LAST_PDF_PATH

    if "file" not in request.files:
        return {"error": "No file uploaded"}, 400

    file = request.files["file"]
    if file.filename == "":
        return {"error": "No file selected"}, 400

    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(base_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)

    # ---------- READ CSV ----------
    try:
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except:
        return {"error": "Invalid CSV file"}, 400

    transactions = []

    for row in rows:
        parsed = parse_transaction_row(row)
        if not parsed:
            continue

        amount, txn_type = parsed
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
            "amount": amount,
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
            total_debit += txn["amount"]
            category_summary[txn["category"]] = category_summary.get(txn["category"], 0) + txn["amount"]
        else:
            total_credit += txn["amount"]

    # ---------- PDF ----------
    report_dir = os.path.join(base_dir, "reports")
    os.makedirs(report_dir, exist_ok=True)

    pdf_path = os.path.join(report_dir, "expense_report.pdf")
    LAST_PDF_PATH = pdf_path

    c = canvas.Canvas(pdf_path, pagesize=A4)
    y = 800

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
            y = 800

        c.drawString(40, y, txn["date"])
        c.drawString(120, y, txn["description"][:25])
        c.drawString(300, y, str(txn["amount"]))
        c.drawString(360, y, txn["type"])
        c.drawString(420, y, txn["category"])
        y -= 15

    y -= 20
    c.setFont("Helvetica-Bold", 12)
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
        return send_file(LAST_PDF_PATH, as_attachment=True, download_name="expense_report.pdf")
    return {"error": "No report available"}, 404


if __name__ == "__main__":
    app.run(debug=True)
