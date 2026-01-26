from flask import Flask, request, send_file, redirect
import os, csv, io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import pdfplumber
from PyPDF2 import PdfReader

app = Flask(__name__)
LAST_PDF_PATH = None


# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect("/upload-form")


@app.route("/upload-form")
def upload_form():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return open(os.path.join(base_dir, "upload.html"), encoding="utf-8").read()


# ---------- UNIVERSAL CSV ROW PARSER ----------
def parse_transaction_row(row):
    def clean(v): return v.replace(",", "").strip()

    for k in ["Debit", "Withdrawal"]:
        if k in row and row[k].strip():
            try:
                return float(clean(row[k])), "debit"
            except:
                return None

    for k in ["Credit", "Deposit"]:
        if k in row and row[k].strip():
            try:
                return float(clean(row[k])), "credit"
            except:
                return None

    if "Amount" in row and row["Amount"].strip():
        try:
            amt = float(clean(row["Amount"]))
        except:
            return None

        for t in ["Type", "Dr/Cr", "DRCR"]:
            if t in row:
                v = row[t].upper()
                if "DR" in v:
                    return abs(amt), "debit"
                if "CR" in v:
                    return abs(amt), "credit"

        return (abs(amt), "debit") if amt < 0 else (amt, "credit")

    return None


# ---------- PDF TEXT EXTRACTION ----------
def extract_text_from_pdf(path, password=None):
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            if not password:
                return None, "PASSWORD_REQUIRED"
            if not reader.decrypt(password):
                return None, "WRONG_PASSWORD"

        text = ""
        with pdfplumber.open(path, password=password) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            return None, "NO_TEXT"

        return text, None

    except Exception as e:
        return None, str(e)


# ---------- UPLOAD ----------
@app.route("/upload", methods=["POST"])
def upload():
    global LAST_PDF_PATH

    if "file" not in request.files:
        return {"error": "No file uploaded"}, 400

    file = request.files["file"]
    password = request.form.get("password")

    if file.filename == "":
        return {"error": "No file selected"}, 400

    base = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(base, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    path = os.path.join(upload_dir, file.filename)
    file.save(path)

    rows = []

    # ---------- CSV ----------
    if file.filename.lower().endswith(".csv"):
        try:
            with open(path, newline="", encoding="utf-8", errors="ignore") as f:
                rows = list(csv.DictReader(f))
        except:
            return {"error": "Invalid CSV file"}, 400

    # ---------- PDF ----------
    elif file.filename.lower().endswith(".pdf"):
        text, status = extract_text_from_pdf(path, password)

        if status == "PASSWORD_REQUIRED":
            return {"error": "PDF is password protected. Please enter password."}, 400

        if status == "WRONG_PASSWORD":
            return {"error": "Incorrect PDF password."}, 400

        if status == "NO_TEXT":
            return {
                "error": "PDF opened but no readable text found. OCR support coming next."
            }, 400

        if text is None:
            return {"error": "Failed to read PDF."}, 400

        # ❗ Phase B2 limitation:
        # PDF text is extracted but not tabular-normalized yet
        return {
            "message": "PDF opened successfully, but structured table parsing is coming next.",
            "raw_preview": text[:1000]
        }

    else:
        return {"error": "Unsupported file type"}, 400

    # ---------- EXPENSE LOGIC (UNCHANGED) ----------
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
            category = "Income"
            total_credit += amount
        else:
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

    # ---------- PDF REPORT ----------
    report_dir = os.path.join(base, "reports")
    os.makedirs(report_dir, exist_ok=True)
    pdf_path = os.path.join(report_dir, "expense_report.pdf")
    LAST_PDF_PATH = pdf_path

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawString(40, 800, "Expense Report")
    c.save()

    return {
        "total_expense": total_debit,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "top_category": max(category_summary, key=category_summary.get) if category_summary else "—",
        "monthly_expense": monthly_expense,
        "monthly_category": monthly_category
    }


# ---------- DOWNLOAD ----------
@app.route("/download-report")
def download_report():
    if LAST_PDF_PATH and os.path.exists(LAST_PDF_PATH):
        return send_file(LAST_PDF_PATH, as_attachment=True)
    return {"error": "No report"}, 404


if __name__ == "__main__":
    app.run(debug=True)
