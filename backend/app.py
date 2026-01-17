# =========================================
# IMPORTS
# =========================================

# Flask is used to create backend server
# request is used to receive files from UI
from flask import Flask, request

# os is used for file and folder paths
import os

# csv is used to read CSV files
import csv


# =========================================
# CREATE FLASK APP
# =========================================

app = Flask(__name__)


# =========================================
# HOME ROUTE (JUST TO CHECK SERVER)
# =========================================

@app.route("/")
def home():
    return "Smart Expense Tracker backend is running!"


# =========================================
# UPLOAD FORM ROUTE (SHOW UI)
# =========================================

@app.route("/upload-form")
def upload_form():
    # Get directory where app.py exists
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Build full path to upload.html
    html_path = os.path.join(base_dir, "upload.html")

    # Return HTML content to browser
    return open(html_path).read()


# =========================================
# FILE UPLOAD + CSV READ ROUTE
# =========================================

@app.route("/upload", methods=["POST"])
def upload():

    # -------- STEP 1: CHECK FILE EXISTS --------
    if "file" not in request.files:
        return "No file part in request"

    file = request.files["file"]

    if file.filename == "":
        return "No file selected"


    # -------- STEP 2: SAVE FILE --------
    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_folder = os.path.join(base_dir, "uploads")

    # Create uploads folder if not exists
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Full file path
    file_path = os.path.join(upload_folder, file.filename)

    # Save file to disk
    file.save(file_path)


    # -------- STEP 3: READ CSV FILE (PHASE 3) --------
    rows = []

    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(row)


    # -------- STEP 4: RETURN DATA (TEMPORARY) --------
    return {
        "message": "CSV file uploaded and read successfully",
        "rows": rows
    }


# =========================================
# RUN SERVER
# =========================================

if __name__ == "__main__":
    app.run(debug=True)
