from flask import Flask, request, send_file, redirect
import os, csv
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader

app = Flask(__name__)
LAST_PDF_PATH = None


@app.route("/")
def home():
    return redirect("/upload-form")


@app.route("/upload-form")
def upload_form():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return open(os.path.join(base_dir, "upload.html"), encoding="utf-8").read()


# ---------- UNIVERSAL ROW PARSER ----------
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


# ---------- PDF TEXT → ROWS ----------
def parse_pdf_text(text):
    rows = []
    lines = text.splitlines()

    for line in lines:
        parts = line.split()
        if len(parts) < 4:
            continue

        # VERY BASIC heuristic (v1)
        try:
            date = parts[0]
            amount = parts[-1]
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

    if "file" not in request.files:
        return {"error": "No file uploaded"}, 400

    file = request.files["file"]
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
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except:
            return {"error": "Invalid CSV file"}, 400

    # ---------- PDF (NO PASSWORD YET) ----------
    elif file.filename.lower().endswith(".pdf"):
        try:
            reader = PdfReader(path)

            if reader.is_encrypted:
                return {"password_required": True}, 200

            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"

            rows = parse_pdf_text(text)

        except Exception as e:
            return {"error": "Unable to read PDF"}, 400

    else:
        return {"error": "Unsupported file type"}, 400

    # ---------- INSIGHTS ----------
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


@app.route("/download-report")
def download_report():
    if LAST_PDF_PATH and os.path.exists(LAST_PDF_PATH):
        return send_file(LAST_PDF_PATH, as_attachment=True)
    return {"error": "No report"}, 404


if __name__ == "__main__":
    app.run(debug=True)
