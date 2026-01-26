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


# ================= ROUTES =================

@app.route("/")
def home():
    return redirect("/upload-form")


@app.route("/upload-form")
def upload_form():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return open(os.path.join(base_dir, "upload.html"), encoding="utf-8").read()


# ================= CSV PARSER =================

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
        if "DR" in t or amt < 0:
            return abs(amt), "debit"
        return amt, "credit"

    return None


# ================= PDF HELPERS =================

def extract_text_pdf(path, password=None):
    try:
        text = ""
        with pdfplumber.open(path, password=password) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text.strip()
    except Exception:
        return ""


def ocr_pdf(path, password=None):
    try:
        images = convert_from_path(path, dpi=300, userpw=password)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img) + "\n"
        return text.strip()
    except Exception:
        return ""


# ================= UNION BANK / OCR PARSER =================

def parse_transactions_from_text(text):
    rows = []

    for line in text.splitlines():
        line = line.strip()

        # Match Union Bank transaction line
        m = re.search(
            r'(?P<date>\d{2}-\d{2}-\d{4})\s+'
            r'(?P<desc>.+?)\s+'
            r'(?P<amount>[\d,]+\.\d+)\((?P<type>Dr|Cr)\)',
            line,
            re.IGNORECASE
        )

        if not m:
            continue

        rows.append({
            "Date": m.group("date"),
            "Description": m.group("desc").strip(),
            "Amount": m.group("amount").replace(",", ""),
            "Type": m.group("type").upper()
        })

    return rows



# ================= UPLOAD =================

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "NO_FILE"}), 400

    file = request.files["file"]
    password = request.form.get("password")

    if file.filename == "":
        return jsonify({"error": "NO_FILE"}), 400

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
            return jsonify({"error": "INVALID_CSV"}), 400

    # ---------- PDF ----------
    elif file.filename.lower().endswith(".pdf"):
        reader = PdfReader(path)

        if reader.is_encrypted and not password:
            return jsonify({"error": "PDF_PASSWORD_REQUIRED"}), 200

        text = extract_text_pdf(path, password=password)

        if not text:
            text = ocr_pdf(path, password=password)

        # 🔴 DEBUG — THIS IS THE ONLY ADDITION
        print("\n===== OCR TEXT START =====")
        print(text[:3000])
        print("===== OCR TEXT END =====\n")

        if not text:
            return jsonify({"error": "NO_TEXT_FOUND"}), 200

        rows = parse_transactions_from_text(text)

        if not rows:
            return jsonify({"error": "NO_TRANSACTIONS_FOUND"}), 200

    else:
        return jsonify({"error": "UNSUPPORTED_FILE"}), 400


    # ================= ANALYSIS =================

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

    return jsonify({
        "total_expense": total_debit,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "top_category": max(category_summary, key=category_summary.get) if category_summary else "—",
        "monthly_expense": monthly_expense,
        "monthly_category": monthly_category
    })


if __name__ == "__main__":
    app.run(debug=True)
