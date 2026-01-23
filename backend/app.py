from flask import Flask, request, send_file, redirect
import os, csv, io
from datetime import datetime
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
LAST_PDF_PATH = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


@app.route("/")
def home():
    return redirect("/upload-form")


@app.route("/upload-form")
def upload_form():
    return open(os.path.join(BASE_DIR, "upload.html"), encoding="utf-8").read()


# ------------------ CSV ROW PARSER ------------------
def parse_transaction_row(row):
    def clean(v): return v.replace(",", "").strip()

    for k in ["Debit", "Withdrawal"]:
        if k in row and row[k].strip():
            return float(clean(row[k])), "debit"

    for k in ["Credit", "Deposit"]:
        if k in row and row[k].strip():
            return float(clean(row[k])), "credit"

    if "Amount" in row and row["Amount"].strip():
        amt = float(clean(row["Amount"]))
        return (abs(amt), "debit") if amt < 0 else (amt, "credit")

    return None


# ------------------ CORE PROCESSOR ------------------
def process_transactions(rows):
    total_debit = total_credit = 0
    category_summary = {}
    monthly_expense = {}
    monthly_category = {}

    for row in rows:
        parsed = parse_transaction_row(row)
        if not parsed:
            continue

        amount, txn_type = parsed
        desc = row.get("Description", "").lower()
        date_str = row.get("Date", "")

        if txn_type == "credit":
            total_credit += amount
            continue

        # Debit categorization
        if "swiggy" in desc or "zomato" in desc:
            category = "Food"
        elif "amazon" in desc or "flipkart" in desc:
            category = "Shopping"
        elif "uber" in desc or "ola" in desc:
            category = "Travel"
        elif "recharge" in desc:
            category = "Utilities"
        else:
            category = "Others"

        total_debit += amount
        category_summary[category] = category_summary.get(category, 0) + amount

        try:
            month = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m")
            monthly_expense[month] = monthly_expense.get(month, 0) + amount
            monthly_category.setdefault(month, {})
            monthly_category[month][category] = monthly_category[month].get(category, 0) + amount
        except:
            pass

    return {
        "total_expense": total_debit,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "top_category": max(category_summary, key=category_summary.get) if category_summary else "—",
        "monthly_expense": monthly_expense,
        "monthly_category": monthly_category
    }


# ------------------ UPLOAD ------------------
@app.route("/upload", methods=["POST"])
def upload():
    global LAST_PDF_PATH

    file = request.files.get("file")
    password = request.form.get("password")

    if not file:
        return {"error": "No file uploaded"}, 400

    filename = file.filename.lower()
    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)

    # ---------- CSV ----------
    if filename.endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        data = process_transactions(rows)

    # ---------- PDF ----------
    elif filename.endswith(".pdf"):
        reader = PdfReader(path)

        if reader.is_encrypted:
            if not password:
                return {"needs_password": True}, 401
            try:
                reader.decrypt(password)
            except:
                return {"error": "Invalid PDF password"}, 403

        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        # VERY BASIC PDF → CSV MOCK (real banks differ)
        rows = []
        for line in text.splitlines():
            parts = line.split(",")
            if len(parts) >= 3:
                rows.append({
                    "Date": parts[0],
                    "Description": parts[1],
                    "Amount": parts[2]
                })

        data = process_transactions(rows)

    else:
        return {"error": "Unsupported file type"}, 400

    # ---------- PDF REPORT ----------
    pdf_path = os.path.join(REPORT_DIR, "expense_report.pdf")
    LAST_PDF_PATH = pdf_path

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawString(40, 800, "Expense Report Summary")
    c.drawString(40, 770, f"Total Expense: ₹ {data['total_expense']}")
    c.drawString(40, 750, f"Top Category: {data['top_category']}")
    c.save()

    return data


@app.route("/download-report")
def download_report():
    if LAST_PDF_PATH and os.path.exists(LAST_PDF_PATH):
        return send_file(LAST_PDF_PATH, as_attachment=True)
    return {"error": "No report available"}, 404


if __name__ == "__main__":
    app.run(debug=True)
