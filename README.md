
# 💳 Smart Expense Tracker

**Turn raw bank statements into meaningful financial insights**

🔗 **Live Demo:** [https://smart-expense-tracker-8e3h.onrender.com](https://smart-expense-tracker-8e3h.onrender.com)

---

## 🚀 Overview

Bank statements are dense, unstructured, and hard to analyze manually — especially PDFs from different banks with varying formats.

**Smart Expense Tracker** solves this by allowing users to upload **CSV or PDF bank statements (including password-protected PDFs)** and instantly get:

* Expense & income summaries
* Category-wise spending
* Monthly debit & credit breakdowns
* Downloadable structured reports

All processing happens **locally on the server** — no data is stored.

---

## ✨ Key Features

### 📂 Universal Statement Support

* ✅ CSV bank statements
* ✅ PDF statements (text-based & OCR-based)
* ✅ Password-protected PDFs (secure prompt)

### 📊 Financial Insights

* Total Expense, Total Debit, Total Credit
* Top spending category
* Monthly debit breakdown
* Monthly credit breakdown
* Smart rule-based insights (spending vs income, peak month, etc.)

### 📑 Structured Reports

* Separate **Debit Report** & **Credit Report**
* Category-wise totals
* Detailed transaction tables (date, description, amount)
* Professionally formatted PDF downloads

### 🎨 Clean UI / UX

* Sidebar-based upload flow
* Fixed action buttons
* Scrollable insights (not the entire page)
* Clear visual separation of debit vs credit
* Mobile-friendly layout

---

## 🧠 Smart Rule-Based Insights (Current)

The system automatically derives insights such as:

* 💸 Expenses higher than income
* ✅ Savings detected
* 📊 Most spent category
* 📆 Highest spending month

> These rules are intentionally deterministic — similar to how early fintech products work before ML is introduced.

---

## 🏗 Architecture Overview

**Flow:**

1. User uploads CSV / PDF
2. Backend detects file type
3. If PDF:
   * Checks encryption
   * Extracts text via `pdfplumber`
   * Falls back to OCR (`Tesseract + Poppler`)
4. Transactions normalized into a common schema
5. Insights generated
6. UI updated dynamically
7. Reports generated on demand

---

## 🛠 Tech Stack

### Backend

* Python 3
* Flask
* Gunicorn (production)
* pdfplumber
* PyPDF2
* pytesseract
* pdf2image
* ReportLab

### Frontend

* HTML
* CSS (custom, no framework)
* Vanilla JavaScript (fetch-based API calls)

### Deployment

* Render (Free tier)

---

## 📂 Project Structure

```bash
Smart-Expense-Tracker/
│
├── app.py
├── upload.html
├── static/
│   ├── style.css
│   └── script.js
├── uploads/
├── reports/
└── requirements.txt
```

---

## ▶️ How to Run Locally

```bash
git clone https://github.com/DeveshreeBhakkad/Smart-Expense-Tracker
cd Smart-Expense-Tracker
pip install -r requirements.txt
python app.py
```

Open:
👉 `http://127.0.0.1:5000`

---

## 🌐 Deployment

The application is deployed on **Render** using:

* `gunicorn app:app`
* Python runtime
* No external database required

🔗 **Live URL:**
https://smart-expense-tracker-8e3h.onrender.com

---

## 🔒 Data Privacy

* No user data is stored
* Uploaded files are processed temporarily
* Passwords are never logged or saved

---

## 🚧 Future Enhancements

* ML-based expense categorization
* Spending trend prediction
* Budget alerts
* User authentication
* Multi-statement comparison
* Export to Excel

---

## 🙌 Why This Project Matters

This project demonstrates:

* Real-world data handling (messy PDFs)
* Backend + frontend integration
* Secure file processing
* Deployment & debugging skills
* Product-thinking, not just coding

---

## Author

Deveshree Bhakkad 

