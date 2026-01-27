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

# ---------- GLOBAL STORE ----------
PARSED_TRANSACTIONS = []

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


# ---------------- CATEGORY DETECTOR (ADDED) ----------------
def detect_category(description):
    d = description.lower()
    if "swiggy" in d or "zomato" in d:
        return "Food"
    if "amazon" in d or "flipkart" in d:
        return "Shopping"
    if "uber" in d or "ola" in d:
        return "Travel"
    if "upi" in d:
        return "UPI"
    return "Others"


# ---------------- UNIVERSAL TRANSACTION MODEL ----------------
def normalize_txn(date, desc, amt, txn_type):
    return {
        "date": date,
        "description": desc.strip(),
        "amount": float(amt),
        "type": txn_type,
        "category": detect_category(desc)
    }


# ---------------- CSV PARSER (UNCHANGED + STORE ADDED) ----------------
def parse_csv(path):
    txns = []
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f):
            for k in ["Debit", "Withdrawal"]:
                if k in row and row[k].strip():
                    txn = normalize_txn(
                        row.get("Date", ""),
                        row.get("Description", ""),
                        row[k].replace(",", ""),
                        "debit"
                    )
                    txns.append(txn)
                    PARSED_TRANSACTIONS.append(txn)

            for k in ["Credit", "Deposit"]:
                if k in row and row[k].strip():
                    txn = normalize_txn(
                        row.get("Date", ""),
                        row.get("Description", ""),
                        row[k].replace(",", ""),
                        "credit"
                    )
                    txns.append(txn)
                    PARSED_TRANSACTIONS.append(txn)
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

    images = convert_from_path(path)
    for img in images:
        text += pytesseract.image_to_string(img)

    return "TEXT", text


# ---------------- OCR TRANSACTION PARSER (FIXED) ----------------
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

        date = None
        for dp in date_patterns:
            m = re.search(dp, line)
            if m:
                date = m.group()
                break
        if not date:
            continue

        amt_match = re.search(amount_pattern, line.replace(",", ""))
        if not amt_match:
            continue

        amount = float(amt_match.group().replace(",", ""))

        if any(k in line_clean for k in debit_keywords):
            txn_type = "debit"
        elif any(k in line_clean for k in credit_keywords):
            txn_type = "credit"
        else:
            continue

        desc = re.sub(date, "", line)
        desc = desc.replace(amt_match.group(), "")
        desc = re.sub(r"(dr|cr|debit|credit)", "", desc, flags=re.I)

        txn = {
            "date": date.replace("/", "-"),
            "description": desc.strip(),
            "amount": amount,
            "type": txn_type,
            "category": detect_category(desc)
        }

        txns.append(txn)
        PARSED_TRANSACTIONS.append(txn)

    return txns


# ---------------- INSIGHTS ENGINE (CREDIT FIXED) ----------------
def generate_insights(txns):
    total_debit = total_credit = 0
    monthly = {}
    monthly_credit = {}
    categories = {}

    # 🔹 NEW (added – safe)
    large_transactions = []
    
    for t in txns:
        amt = t["amount"]
        date = t["date"]
        desc = t["description"].lower()

        # -------- DEBIT --------
        if t["type"] == "debit":
            total_debit += amt
            cat = t["category"]
            categories[cat] = categories.get(cat, 0) + amt

            # monthly debit
            try:
                m = datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m")
                monthly[m] = monthly.get(m, 0) + amt
            except:
                pass

            # large transaction flag (added)
            if amt >= 5000:
                large_transactions.append(t)

        # -------- CREDIT --------
        else:
            total_credit += amt
            try:
                m = datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m")
                monthly_credit[m] = monthly_credit.get(m, 0) + amt
            except:
                pass

            # large transaction flag (added)
            if amt >= 5000:
                large_transactions.append(t)

    # 🔹 NEW INSIGHTS (added safely)
    highest_spending_month = (
        max(monthly, key=monthly.get) if monthly else None
    )

    net_status = (
        "Saver" if total_credit > total_debit else "Spender"
    )

    expense_ratio = (
        round((total_debit / total_credit) * 100, 2)
        if total_credit > 0 else None
    )

    # 🔹 FINAL RESPONSE (existing keys preserved + new keys added)
    return {
        # existing (DO NOT TOUCH)
        "total_expense": total_debit,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "top_category": max(categories, key=categories.get) if categories else "—",
        "monthly_expense": monthly,
        "monthly_credit": monthly_credit,

        # 🔥 added insights
        "highest_spending_month": highest_spending_month,
        "net_status": net_status,
        "expense_ratio": expense_ratio,
        "large_transaction_count": len(large_transactions)
    }

# ---------------- UPLOAD ENDPOINT ----------------
@app.route("/upload", methods=["POST"])
def upload():
    global LAST_PDF_PATH, PARSED_TRANSACTIONS
    PARSED_TRANSACTIONS = []

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

    pdf_path = os.path.join(REPORT_DIR, "expense_report.pdf")
    LAST_PDF_PATH = pdf_path
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawString(40, 800, "Expense Report")
    c.save()

    return jsonify(insights)


# ---------------- DOWNLOAD REPORT ----------------
@app.route("/download-report")
def download_report():
    report_type = request.args.get("type")  # debit or credit

    if not PARSED_TRANSACTIONS:
        return jsonify({
            "error": "NO_DATA",
            "message": "Please analyze a statement before downloading report."
        })

    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.lib import colors

    output_path = os.path.join(BASE_DIR, f"{report_type}_report.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    story = []

    title = "Expense Report (Debit)" if report_type == "debit" else "Credit Report"
    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 0.3 * inch))

    filtered = [t for t in PARSED_TRANSACTIONS if t["type"] == report_type]

    if not filtered:
        story.append(Paragraph("No transactions found.", styles["Normal"]))
        doc.build(story)
        return send_file(output_path, as_attachment=True)

    # -------- GROUP BY CATEGORY --------
    category_map = {}
    for txn in filtered:
        category_map.setdefault(txn["category"], []).append(txn)

    grand_total = 0

    for category, txns in category_map.items():
        total = sum(t["amount"] for t in txns)
        grand_total += total

        story.append(Spacer(1, 0.2 * inch))
        story.append(
            Paragraph(f"<b>{category} — ₹ {total:.2f}</b>", styles["Heading2"])
        )
        story.append(Spacer(1, 0.1 * inch))

        # -------- TABLE DATA (FIXED) --------
        table_data = [
            [
                Paragraph("Date", styles["Normal"]),
                Paragraph("Description", styles["Normal"]),
                Paragraph("Amount (₹)", styles["Normal"]),
            ]
        ]

        for t in txns:
            table_data.append([
                Paragraph(t["date"], styles["Normal"]),
                Paragraph(t["description"], styles["Normal"]),
                Paragraph(f"{t['amount']:.2f}", styles["Normal"])
            ])

        table = Table(
            table_data,
            colWidths=[80, 300, 80],
            repeatRows=1
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ]))

        story.append(table)

    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            f"<b>GRAND TOTAL — ₹ {grand_total:.2f}</b>",
            styles["Heading1"]
        )
    )

    doc.build(story)
    return send_file(output_path, as_attachment=True)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


