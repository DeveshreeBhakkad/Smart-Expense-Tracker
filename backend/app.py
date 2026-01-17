# -----------------------------
# IMPORTS
# -----------------------------

# Flask is used to create the backend server
# request is used to receive data (files, forms) from frontend
from flask import Flask, request

# os is used to safely work with file paths
import os


# -----------------------------
# CREATE FLASK APP
# -----------------------------

# This creates the Flask application (backend)
app = Flask(__name__)


# -----------------------------
# HOME ROUTE
# -----------------------------
# This route is just to check if backend is running

@app.route("/")
def home():
    return "Smart Expense Tracker backend is running!"


# -----------------------------
# UPLOAD FORM ROUTE (UI)
# -----------------------------
# This route shows the HTML upload page in browser

@app.route("/upload-form")
def upload_form():
    # Get the directory where app.py is located
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Create full path to upload.html
    html_path = os.path.join(base_dir, "upload.html")

    # Open and return HTML file content
    return open(html_path).read()


# -----------------------------
# FILE UPLOAD ROUTE (LOGIC)
# -----------------------------
# This route receives the uploaded file from UI

@app.route("/upload", methods=["POST"])
def upload():
    # Step 1: Check if file key exists in request
    if "file" not in request.files:
        return "No file part in request"

    # Step 2: Get the file object
    file = request.files["file"]

    # Step 3: Check if user selected a file
    if file.filename == "":
        return "No file selected"

    # Step 4: Build safe path to uploads folder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_folder = os.path.join(base_dir, "uploads")

    # Step 5: Create uploads folder if it doesn't exist
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Step 6: Full path where file will be saved
    file_path = os.path.join(upload_folder, file.filename)

    # Step 7: Save file to disk
    file.save(file_path)

    # Step 8: Send success message
    return f"File '{file.filename}' uploaded successfully!"


# -----------------------------
# RUN THE SERVER
# -----------------------------

# This ensures the app runs only when app.py is executed directly
if __name__ == "__main__":
    app.run(debug=True)
