from flask import Flask, request, send_file, redirect, jsonify
import os, csv, re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# PDF / OCR
import pdfplumber
from PyPDF2 import PdfReader
import pytesseract
from pdf2image import convert_from_path

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

LAST_PDF_PATH = None


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return redirect("/upload-form")


@app.route("/upload-form")
def upload_form():
    return open(os.path.join(BASE_DIR, "upload.html"), encoding="utf-8").read()


# ---------------- UNIVERSAL TRANSACTION MODEL ----------------
def normalize_txn(date, desc, amt, txn_type):
    return {
        "date": date,
        "description": desc.strip(),
        "amount": float(amt),
        "type": txn_type
    }


# ---------------- CSV PARSER (UNCHANGED) ----------------
def parse_csv(path):
    txns = []
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f):
            for k in ["Debit", "Withdrawal"]:
                if k in row and row[k].strip():
                    txns.append(normalize_txn(
                        row.get("Date", ""),
                        row.get("Description", ""),
                        row[k].replace(",", ""),
                        "debit"
                    ))

            for k in ["Credit", "Deposit"]:
                if k in row and row[k].strip():
                    txns.append(normalize_txn(
                        row.get("Date", ""),
                        row.get("Description", ""),
                        row[k].replace(",", ""),
                        "credit"
                    ))
    return txns


# ---------------- OCR TEXT EXTRACTION ----------------
def extract_pdf_text(path, password=None):
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            if not password:
                return "PASSWORD_REQUIRED", None
            if not reader.decrypt(password):
                return "INCORRECT_PASSWORD", None
    except:
        pass

    text = ""

    try:
        with pdfplumber.open(path, password=password) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except:
        pass

    if text.strip():
        return "TEXT", text

    # OCR fallback
    images = convert_from_path(path)
    for img in images:
        text += pytesseract.image_to_string(img)

    return "TEXT", text


# ---------------- UNIVERSAL OCR TRANSACTION PARSER ----------------
def parse_ocr_text(text):
    txns = []

    date_patterns = [
        r"\d{2}-\d{2}-\d{4}",
        r"\d{2}/\d{2}/\d{4}"
    ]

    amount_pattern = r"([\d,]+(?:\.\d{1,2})?)"
    debit_keywords = ["dr", "debit"]
    credit_keywords = ["cr", "credit"]

    for line in text.splitlines():
        line_clean = line.lower()

        # detect date
        date = None
        for dp in date_patterns:
            m = re.search(dp, line)
            if m:
                date = m.group()
                break
        if not date:
            continue

        # detect amount
        amt_match = re.search(amount_pattern, line.replace(",", ""))
        if not amt_match:
            continue
        amount = amt_match.group().replace(",", "")

        # detect type
        txn_type = None
        if any(k in line_clean for k in debit_keywords):
            txn_type = "debit"
        elif any(k in line_clean for k in credit_keywords):
            txn_type = "credit"
        else:
            continue  # cannot decide type

        # description cleanup
        desc = line
        desc = re.sub(date, "", desc)
        desc = desc.replace(amt_match.group(), "")
        desc = re.sub(r"(dr|cr|debit|credit)", "", desc, flags=re.I)

        txns.append({
            "date": date.replace("/", "-"),
            "description": desc.strip(),
            "amount": float(amount),
            "type": txn_type
        })

    return txns


# ---------------- INSIGHTS ENGINE ----------------
def generate_insights(txns):
    total_debit = total_credit = 0
    monthly = {}
    categories = {}

    for t in txns:
        amt = t["amount"]
        date = t["date"]
        desc = t["description"].lower()

        if t["type"] == "debit":
            total_debit += amt
            if "swiggy" in desc or "zomato" in desc:
                cat = "Food"
            elif "amazon" in desc or "flipkart" in desc:
                cat = "Shopping"
            elif "upi" in desc:
                cat = "UPI"
            else:
                cat = "Others"

            categories[cat] = categories.get(cat, 0) + amt

            try:
                m = datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m")
                monthly[m] = monthly.get(m, 0) + amt
            except:
                pass

        else:
            total_credit += amt

    return {
        "total_expense": total_debit,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "top_category": max(categories, key=categories.get) if categories else "—",
        "monthly_expense": monthly
    }


# ---------------- UPLOAD ENDPOINT ----------------
@app.route("/upload", methods=["POST"])
def upload():
    global LAST_PDF_PATH

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)

    txns = []

    if file.filename.lower().endswith(".csv"):
        txns = parse_csv(path)

    elif file.filename.lower().endswith(".pdf"):
        password = request.form.get("password")
        status, text = extract_pdf_text(path, password)

        if status == "PASSWORD_REQUIRED":
            return jsonify({"error": "PASSWORD_REQUIRED"})
        if status == "INCORRECT_PASSWORD":
            return jsonify({"error": "INCORRECT_PASSWORD"})

        txns = parse_ocr_text(text)

    if not txns:
        return jsonify({"error": "NO_TRANSACTION_FOUND"})

    insights = generate_insights(txns)

    # Simple PDF report
    pdf_path = os.path.join(REPORT_DIR, "expense_report.pdf")
    LAST_PDF_PATH = pdf_path
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawString(40, 800, "Expense Report")
    y = 760
    for k, v in insights.items():
        c.drawString(40, y, f"{k}: {v}")
        y -= 20
    c.save()

    return jsonify(insights)


@app.route("/download-report")
def download_report():
    report_type = request.args.get("type")  # debit or credit

    if not LAST_PDF_PATH or not os.path.exists(LAST_PDF_PATH):
        return {"error": "No report available"}, 404

    # Data already prepared earlier during upload
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import inch

    base = os.path.dirname(os.path.abspath(__file__))
    output = os.path.join(base, f"{report_type}_report.pdf")

    doc = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title = "Expense Report" if report_type == "debit" else "Credit Report"
    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 0.3 * inch))

    data_source = request.environ.get("parsed_transactions", [])

    category_map = {}

    for txn in data_source:
        if txn["type"] != report_type:
            continue

        cat = txn["category"]
        category_map.setdefault(cat, [])
        category_map[cat].append(txn)

    for cat, txns in category_map.items():
        total = sum(t["amount"] for t in txns)
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"<b>{cat} — ₹ {total}</b>", styles["Heading2"]))

        for t in txns:
            line = f"{t['date']} | {t['description']} | ₹ {t['amount']} | {t['type'].upper()}"
            story.append(Paragraph(line, styles["Normal"]))

    doc.build(story)

    return send_file(output, as_attachment=True)



if __name__ == "__main__":
    app.run(debug=True)
