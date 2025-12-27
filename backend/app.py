from flask import Flask , request
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Smart Expense Tracker backend is running!"

@app.route("/health")
def health():
    return "Backend is healthy"

@app.route("/tracker")
def tracker():
    return "Tracking in Progress..."

@app.route("/upload-form")
def upload_form():
    return open ("backend/upload.html").read()

@app.route("/upload" , methods=["POST"])
def upload():
    if "file" not in request.files:
        return "No file part in request"
    
    file = request.files["files"]

    if file.filename == "":
        return "No file selected"
    
    upload_path = os.path.join("backend" , "uploads" , file.filename)
    file.save(upload_path)

    return f"File '{file.filename}' uploaded successfully!"


if __name__ == "__main__":
    app.run(debug=True)


    

