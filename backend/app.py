from flask import Flask, request, send_file, redirect
import os, csv, time
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pypdf import PdfReader

app = Flask(__name__, static_folder="../static")

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


# ---------- TRANSACTION PARSER ----------
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
        return abs(amt), "debit" if amt < 0 else "credit"

    return None


# ---------- PDF TEXT EXTRACTION ----------
def extract_text_from_pdf(path, password=None):
    reader = PdfReader(path)

    if reader.is_encrypted:
        if not password:
            return None, "PASSWORD_REQUIRED"
        if not reader.decrypt(password):
            return None, "WRONG_PASSWORD"

    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    return text, None


def pdf_text_to_rows(text):
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue

        try:
            date = parts[0]
            amount = parts[-1].replace(",", "")
            float(amount)
            desc = " ".join(parts[1:-1])

            rows.append({
                "Date": date,
                "Description": desc,
                "Amount": amount
            })
        except:
            continue

    return rows


# ---------- UPLOAD ----------
@app.route("/upload", methods=["POST"])
def upload():
    global LAST_PDF_PATH

    file = request.files.get("file")
    password = request.form.get("password")

    if not file or file.filename == "":
        return {"error": "No file uploaded"}, 400

    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)

    rows = []

    # ---- CSV ----
    if file.filename.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    # ---- PDF ----
    elif file.filename.lower().endswith(".pdf"):
        text, err = extract_text_from_pdf(path, password)

        if err == "PASSWORD_REQUIRED":
            return {"password_required": True}

        if err == "WRONG_PASSWORD":
            return {"error": "Incorrect PDF password"}

        rows = pdf_text_to_rows(text)

    else:
        return {"error": "Unsupported file type"}

    # ---------- PROCESS ----------
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

        if "swiggy" in desc or "zomato" in desc:
            category = "Food"
        elif "amazon" in desc or "flipkart" in desc:
            category = "Shopping"
        elif "uber" in desc or "ola" in desc:
            category = "Travel"
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

    # ---------- PDF REPORT ----------
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
        "top_category": max(category_summary, key=category_summary.get) if category_summary else "—",
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
