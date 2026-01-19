from flask import Flask, request, send_file, redirect
import os
import csv
from datetime import datetime
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
    def clean(val):
        return val.replace(",", "").strip()

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

    if "Amount" in row and row["Amount"].strip():
        try:
            amount = float(clean(row["Amount"]))
        except:
            return None

        txn_type = None
        for type_key in ["Type", "Dr/Cr", "DRCR"]:
            if type_key in row:
                value = row[type_key].upper()
                if "DR" in value:
                    txn_type = "debit"
                elif "CR" in value:
                    txn_type = "credit"

        if txn_type:
            return abs(amount), txn_type

        return (abs(amount), "debit") if amount < 0 else (amount, "credit")

    return None


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

    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(base_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)

    try:
        with open(file_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
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
            "amount": amount,
            "type": txn_type,
            "category": category
        })

    if not transactions:
        return {"error": "No valid transactions"}, 400

    # ===============================
    # SUMMARY + MONTHLY INSIGHTS
    # ===============================
    category_summary = {}
    monthly_expense = {}
    total_debit = 0
    total_credit = 0

    for txn in transactions:
        if txn["type"] == "debit":
            total_debit += txn["amount"]
            category_summary[txn["category"]] = category_summary.get(txn["category"], 0) + txn["amount"]

            # Monthly calculation
            try:
                dt = datetime.strptime(txn["date"], "%Y-%m-%d")
                month_key = dt.strftime("%Y-%m")
                monthly_expense[month_key] = monthly_expense.get(month_key, 0) + txn["amount"]
            except:
                pass

        else:
            total_credit += txn["amount"]

    # ===============================
    # PDF (unchanged)
    # ===============================
    report_dir = os.path.join(base_dir, "reports")
    os.makedirs(report_dir, exist_ok=True)

    pdf_path = os.path.join(report_dir, "expense_report.pdf")
    LAST_PDF_PATH = pdf_path

    c = canvas.Canvas(pdf_path, pagesize=A4)
    y = 800
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Expense Report")
    c.save()

    return {
        "total_debit": total_debit,
        "total_credit": total_credit,
        "category_summary": category_summary,
        "monthly_expense": monthly_expense
    }


# ===============================
# DOWNLOAD
# ===============================
@app.route("/download-report")
def download_report():
    if LAST_PDF_PATH and os.path.exists(LAST_PDF_PATH):
        return send_file(LAST_PDF_PATH, as_attachment=True)
    return {"error": "No report available"}, 404


if __name__ == "__main__":
    app.run(debug=True)
