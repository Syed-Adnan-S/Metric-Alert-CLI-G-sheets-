# 📊 Google Sheets Metric Alert CLI Tool

A configurable automation tool that:

- Reads metric comparisons from Google Sheets
- Evaluates rule-based thresholds
- Sends styled HTML email alerts
- Logs alerts to a Google Sheet
- Supports CLI modes (dry run, no-email, etc.)

---

## 🚀 Features

- Config-driven rule engine
- HTML email formatting
- CLI flags:
  - `--dry-run`
  - `--no-email`
  - `--no-sheet-log`
  - `--verbose`
- Google Sheets logging
- Error logging (`alerts.log`)

---

## ⚙️ Setup

1. Clone the repository
2. Create virtual environment:
    python -m venv venv
    venv\Scripts\activate
3. Install dependencies:
    pip install -r requirements.txt
4. Create a `.env` file:
    SHEET_ID=your_sheet_id
    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_USER=your_email
    EMAIL_APP_PASSWORD=your_app_password
    EMAIL_SENDER_NAME=Metrics Bot

5. Add your Google service account JSON file.

---

## ▶️ Usage

Normal run: python alert_engine.py

Dry run: python alert_engine.py --dry-run --verbose

Disable email: python alert_engine.py --no-email

---

## 🔒 Security

Do NOT upload:
- `.env`
- Service account JSON file
