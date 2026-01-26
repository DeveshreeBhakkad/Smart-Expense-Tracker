from flask import Flask, request, send_file, redirect, jsonify
import os, csv, re
from datetime import datetime

import pdfplumber
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
LAST_PDF_PATH = None


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return redirect("/upload-form")


@app.route("/upload-form")
def upload_form():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return open(os.path.join(base_dir, "upload.html"), encoding="utf-8").read()


# ---------------- CSV PARSER ----------------

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
        t = row.get("Type", "").upper()
        return (abs(amt), "debit") if "DR" in t or amt < 0 else (amt, "credit")

    return None


# ---------------- PDF HELPERS ----------------

def extract_text_pdf(path):
    try:
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text.strip()
    except Exception as e:
        print("PDF TEXT ERROR:", e)
        return ""


def ocr_pdf(path, password=None):
    try:
        images = convert_from_path(
            path,
            dpi=300,
            userpw=password
        )
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img) + "\n"
        return text.strip()
    except Exception as e:
        print("OCR ERROR:", e)
        return ""


def parse_transactions_from_text(text):
    rows = []
    lines = text.splitlines()

    for line in lines:
        m = re.search(r'(\d{2}[-/]\d{2}[-/]\d{4}).*?([\d,]+\.\d{2})', line)
        if m:
            rows.append({
                "Date": m.group(1).replace("/", "-"),
                "Amount": m.group(2).replace(",", ""),
                "Description": line
            })
    return rows


# ---------------- UPLOAD ----------------

@app.route("/upload", methods=["POST"])
def upload():
    global LAST_PDF_PATH

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    password = request.form.get("password")

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

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
            return jsonify({"error": "Invalid CSV"}), 400

    # ---------- PDF ----------
    elif file.filename.lower().endswith(".pdf"):
        try:
            reader = PdfReader(path)
            if reader.is_encrypted and not password:
                return jsonify({
                    "error": "PDF_PASSWORD_REQUIRED",
                    "message": "PDF is password protected. Please enter password."
                }), 200
        except Exception as e:
            print("PDF OPEN ERROR:", e)
            return jsonify({"error": "Invalid PDF"}), 400

        text = extract_text_pdf(path)

        if not text:
            text = ocr_pdf(path, password=password)

        if not text:
            return jsonify({
                "error": "NO_TEXT_FOUND",
                "message": "PDF opened but no readable text could be extracted."
            }), 200

        rows = parse_transactions_from_text(text)

        if not rows:
            return jsonify({
                "error": "NO_TRANSACTIONS_FOUND",
                "message": "PDF text extracted but no transaction data detected."
            }), 200

    else:
        return jsonify({"error": "Unsupported file type"}), 400


    # ---------------- ANALYSIS ----------------

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
        else:
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
                monthly_category[month][category] = (
                    monthly_category[month].get(category, 0) + amount
                )
            except:
                pass


    # ---------------- PDF REPORT ----------------

    report_dir = os.path.join(base, "reports")
    os.makedirs(report_dir, exist_ok=True)
    pdf_path = os.path.join(report_dir, "expense_report.pdf")
    LAST_PDF_PATH = pdf_path

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawString(40, 800, "Expense Report")
    c.save()

    return jsonify({
        "total_expense": total_debit,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "top_category": max(category_summary, key=category_summary.get) if category_summary else "—",
        "monthly_expense": monthly_expense,
        "monthly_category": monthly_category
    })


@app.route("/download-report")
def download_report():
    if LAST_PDF_PATH and os.path.exists(LAST_PDF_PATH):
        return send_file(LAST_PDF_PATH, as_attachment=True)
    return jsonify({"error": "No report"}), 404


if __name__ == "__main__":
    app.run(debug=True)
