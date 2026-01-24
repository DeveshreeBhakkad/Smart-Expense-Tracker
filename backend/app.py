from flask import Flask, request, send_file, redirect
import os, csv
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__, static_folder="static")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

LAST_PDF_PATH = None


@app.route("/")
def home():
    return redirect("/upload-form")


@app.route("/upload-form")
def upload_form():
    return open(os.path.join(BASE_DIR, "upload.html"), encoding="utf-8").read()


# ---------- CSV PARSER ----------


@app.route("/upload", methods=["POST"])
def upload():
    global LAST_PDF_PATH

    if "file" not in request.files:
        return {"error": "No file uploaded"}, 400

    file = request.files["file"]
    if file.filename == "":
        return {"error": "No file selected"}, 400

    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)

    rows = []

    try:
       with open(path, newline="", encoding="utf-8") as f:
          rows = list(csv.DictReader(f))
    except UnicodeDecodeError:
       with open(path, newline="", encoding="latin-1") as f:
          rows = list(csv.DictReader(f))

    total_debit = 0
    total_credit = 0
    monthly_expense = {}
    monthly_category = {}

    for row in rows:
        parsed = parse_transaction_row(row)
        if not parsed:
            continue

        amount, txn_type = parsed
        date = row.get("Date", "")
        desc = row.get("Description", "").lower()

        if txn_type == "credit":
            total_credit += amount
            continue

        total_debit += amount

        if "swiggy" in desc or "zomato" in desc:
            category = "Food"
        elif "amazon" in desc or "flipkart" in desc:
            category = "Shopping"
        else:
            category = "Others"

        try:
            month = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m")
            monthly_expense[month] = monthly_expense.get(month, 0) + amount
            monthly_category.setdefault(month, {})
            monthly_category[month][category] = monthly_category[month].get(category, 0) + amount
        except:
            pass

    pdf_path = os.path.join(REPORT_DIR, "expense_report.pdf")
    LAST_PDF_PATH = pdf_path

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawString(40, 800, "Expense Report")
    c.drawString(40, 770, f"Total Expense: ₹ {total_debit}")
    c.save()

    return {
        "total_expense": total_debit,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "top_category": max(
            (cat for m in monthly_category.values() for cat in m),
            default="—"
        ),
        "monthly_expense": monthly_expense,
        "monthly_category": monthly_category
    }


@app.route("/download-report")
def download_report():
    if LAST_PDF_PATH and os.path.exists(LAST_PDF_PATH):
        return send_file(LAST_PDF_PATH, as_attachment=True)
    return {"error": "No report"}, 404


if __name__ == "__main__":
    app.run(debug=True)
