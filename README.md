# Smart Expense Tracker 💸

Smart Expense Tracker is a Flask-based web application that analyzes bank statements
(CSV currently, PDF support in progress) and presents clean, human-friendly insights
about spending behavior.

The focus of this project is:
- Real-world statement parsing
- Clean backend logic
- A pleasant, website-like UI (not a dashboard)
- Gradual feature expansion with stability

---

## ✨ Features Implemented (Working)

### 1. CSV Upload & Analysis
- Upload bank statement CSV files
- Supports multiple bank formats:
  - Debit / Credit
  - Withdrawal / Deposit
  - Amount + DR/CR columns
- Automatically detects:
  - Debit vs Credit
  - Transaction amount
  - Description
  - Date

### 2. Expense Insights
- Total Expense
- Total Debit
- Total Credit
- Top Spending Category
- Monthly Expenses
- Category-wise breakdown inside each month (expand/collapse)

### 3. Smart Categorization
Transactions are categorized using description keywords:
- Food (Swiggy, Zomato)
- Shopping (Amazon, Flipkart)
- Travel (Uber, Ola)
- Utilities (Recharge)
- Others (fallback)

### 4. PDF Report Generation
- Generates a basic expense PDF report
- Downloadable from UI

### 5. Clean UI (High Priority)
- Dark, modern theme
- Website-like experience
- Expandable monthly insights
- UI kept **stable intentionally**

---

## 🧪 In Progress (Not Final Yet)

### PDF Statement Parsing
- Detects password-protected PDFs
- UI shows warning when PDF is encrypted
- Password input UI exists
- Actual PDF text extraction logic still under refinement

⚠️ PDF parsing is **not stable yet** and intentionally paused to avoid breaking the app.

---

## 📂 Project Structure
```bash
Smart-Expense-Tracker/
│
├── backend/
│ ├── app.py
│ ├── upload.html
│ ├── uploads/
│ ├── reports/
│ └── static/
│  ├── style.css
│  └── script.js
│
├── venv/
└── README.md
```
---


> Note:  
All frontend files (`upload.html`, `static/`) live **inside the backend folder**.

---

## ▶️ How to Run

```bash
python backend/app.py
```
