from flask import Flask, request, send_file
import csv, os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

LAST_REPORT_PATH = None


# ===============================
# ROOT CHECK
# ===============================
@app.route("/")
def home():
    return {
        "message": "Smart Expense Tracker backend is running",
        "ui": "/ui",
        "upload": "POST /upload"
    }


# ===============================
# SIMPLE UI (NO TEMPLATES)
# ===============================
@app.route("/ui")
def ui():
    return open(os.path.join(BASE_DIR, "upload.html")).read()


# ===============================
# STEP 1 — CSV NORMALIZATION
# ===============================
def normalize_csv(file_path):
    normalized = []

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                amount = None
                txn_type = None

                def clean(v):
                    return float(v.replace(",", "").strip())

                # Debit / Withdrawal
                for k in ["Debit", "Withdrawal"]:
                    if k in row and row[k].strip():
                        amount = clean(row[k])
                        txn_type = "debit"

                # Credit / Deposit
                for k in ["Credit", "Deposit"]:
                    if k in row and row[k].strip():
                        amount = clean(row[k])
                        txn_type = "credit"

                # Amount + sign / type
                if amount is None and "Amount" in row and row["Amount"].strip():
                    raw = clean(row["Amount"])
                    amount = abs(raw)
                    txn_type = "debit" if raw < 0 else "credit"

                if amount is None:
                    continue

                normalized.append({
                    "date": row.get("Date", ""),
                    "description": row.get("Description", ""),
                    "amount": amount,
                    "type": txn_type
                })

            except:
                continue

    return normalized


# ===============================
# STEP 2 — CATEGORY INSIGHTS
# ===============================
def category_insights(transactions):
    categories = {}
    total = 0

    for tx in transactions:
        if tx["type"] != "debit":
            continue

        desc = tx["description"].lower()
        amt = tx["amount"]

        if "swiggy" in desc or "zomato" in desc:
            cat = "Food"
        elif "amazon" in desc or "flipkart" in desc:
            cat = "Shopping"
        elif "uber" in desc or "ola" in desc:
            cat = "Travel"
        else:
            cat = "Others"

        categories[cat] = categories.get(cat, 0) + amt
        total += amt

    percentages = {
        c: round((a / total) * 100, 2)
        for c, a in categories.items()
    } if total else {}

    return categories, percentages


# ===============================
# STEP 3 — MERCHANT INSIGHTS
# ===============================
def merchant_insights(transactions):
    merchants = {}

    for tx in transactions:
        if tx["type"] != "debit":
            continue

        name = tx["description"].split()[0]
        merchants.setdefault(name, {"count": 0, "total": 0})

        merchants[name]["count"] += 1
        merchants[name]["total"] += tx["amount"]

    return merchants


# ===============================
# STEP 4 — PDF REPORT
# ===============================
def generate_pdf(categories, percentages, merchants):
    global LAST_REPORT_PATH

    pdf_path = os.path.join(REPORT_DIR, "expense_report.pdf")
    LAST_REPORT_PATH = pdf_path

    c = canvas.Canvas(pdf_path, pagesize=A4)
    y = 800

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Smart Expense Tracker Report")
    y -= 30

    c.setFont("Helvetica", 11)
    c.drawString(40, y, "Category Breakdown:")
    y -= 20

    for cat, amt in categories.items():
        c.drawString(50, y, f"{cat}: ₹{amt} ({percentages.get(cat, 0)}%)")
        y -= 15

    y -= 20
    c.drawString(40, y, "Top Merchants:")
    y -= 20

    for m, d in merchants.items():
        c.drawString(50, y, f"{m}: {d['count']} txns, ₹{d['total']}")
        y -= 15

    c.save()


# ===============================
# UPLOAD ROUTE
# ===============================
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return {"error": "No file uploaded"}, 400

    file = request.files["file"]
    if not file.filename:
        return {"error": "Empty filename"}, 400

    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)

    transactions = normalize_csv(path)
    categories, percentages = category_insights(transactions)
    merchants = merchant_insights(transactions)

    generate_pdf(categories, percentages, merchants)

    return {
        "transactions_processed": len(transactions),
        "categories": categories,
        "category_percentages": percentages,
        "top_merchants": merchants
    }


# ===============================
# DOWNLOAD PDF
# ===============================
@app.route("/download-report")
def download_report():
    if LAST_REPORT_PATH:
        return send_file(LAST_REPORT_PATH, as_attachment=True)
    return {"error": "No report available"}, 404


if __name__ == "__main__":
    app.run(debug=True)
