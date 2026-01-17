from flask import Flask, request
import os
import csv

app = Flask(__name__)


@app.route("/")
def home():
    return "Smart Expense Tracker backend is running!"


@app.route("/upload-form")
def upload_form():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "upload.html")
    return open(html_path).read()


@app.route("/upload", methods=["POST"])
def upload():

    # ---------- FILE CHECK ----------
    if "file" not in request.files:
        return "No file part in request"

    file = request.files["file"]

    if file.filename == "":
        return "No file selected"


    # ---------- SAVE FILE ----------
    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_folder = os.path.join(base_dir, "uploads")

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    file_path = os.path.join(upload_folder, file.filename)
    file.save(file_path)


    # ---------- READ CSV ----------
    rows = []

    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(row)


    # ---------- NORMALIZE TRANSACTIONS ----------
    normalized_transactions = []

    for row in rows:
        raw_amount = float(row["Amount"])

        # CASE 1: DR / CR column exists (official statements)
        if "Type" in row and row["Type"]:
            if row["Type"].strip().upper() in ["DR", "DEBIT"]:
                txn_type = "debit"
            else:
                txn_type = "credit"

            amount_value = raw_amount

        # CASE 2: No Type column → use sign
        else:
            if raw_amount < 0:
                txn_type = "debit"
                amount_value = abs(raw_amount)
            else:
                txn_type = "credit"
                amount_value = raw_amount


        normalized_transactions.append({
            "date": row.get("Date", ""),
            "description": row.get("Description", ""),
            "amount": amount_value,
            "type": txn_type
        })


    return {
        "message": "CSV uploaded and normalized using bank-style logic",
        "transactions": normalized_transactions
    }


if __name__ == "__main__":
    app.run(debug=True)
