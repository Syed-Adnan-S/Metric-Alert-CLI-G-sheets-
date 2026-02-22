# 📊 Google Sheets Metric Alert CLI Tool

A lightweight, configurable alert engine that monitors business metrics directly from Google Sheets.

It evaluates rule-based thresholds (MoM / YoY), sends styled HTML email alerts, and logs alert activity — all controlled via a simple Config tab.

---

## 🔄 How It Works

1. Metrics are updated in the **Latest** tab of a Google Sheet.
2. Alert rules are defined in the **Config** tab.
3. The script:
   - Reads latest metric values
   - Evaluates threshold rules
   - Sends HTML email alerts if conditions are met
   - Logs sent alerts to the **Logs** tab
4. CLI flags allow safe testing (dry-run, no-email, etc.)

No code changes are required — all alert behavior is controlled from the Google Sheet.

---

## 🚀 Features

- Config-driven rule engine
- MoM / YoY threshold evaluation
- HTML formatted email alerts
- Google Sheets audit logging
- Local error logging (`alerts.log`)
- CLI support:
  - `--dry-run`
  - `--no-email`
  - `--no-sheet-log`
  - `--verbose`

---

## 📊 Google Sheets Template

View-only template (shows required structure):

👉 https://docs.google.com/spreadsheets/d/1e1dZAEHh5SkuMESbV9iQVawx--Lgq5YmOa6WPweIdzM/edit?usp=sharing

The template contains:

### Latest Tab
Stores the most recent month’s values and comparisons.

### Config Tab
Defines alert rules (thresholds, direction, recipients, enable/disable).

### Logs Tab
Stores all alert history and audit information.

---

## ⚡ Quick Start (Experiment Mode)

To test the system quickly:

1. Clone this repository
2. Open the template sheet
3. Click **File → Make a copy**
4. Update the `Latest` and `Config` tabs
5. Create a `.env` file (see below)
6. Add your Google service account JSON file
7. Run:

```bash
python alert_engine.py --dry-run --verbose
```

If everything looks correct, run without --dry-run to send emails.

---

## 🛠 Setup Instructions

1️⃣ Clone the Repository

```bash
git clone <your_repo_url>
cd google-sheets-metric-alert-cli
```

2️⃣ Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

4️⃣ Create .env File

Create a file named .env in the project root with the following content:

```bash
SHEET_ID=your_sheet_id_here
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email
EMAIL_APP_PASSWORD=your_gmail_app_password
EMAIL_SENDER_NAME=Metrics Bot
```
👉 SHEET_ID is the value between /d/ and /edit in the Google Sheets URL.

5️⃣ Add Google Service Account
  - Enable Google Sheets API in Google Cloud
  - Create a Service Account
  - Download the JSON key file
  - Place it in the project root
  - Share your Google Sheet with the service account email

---

## ▶️ CLI Usage

Normal run: python alert_engine.py

Dry run: python alert_engine.py --dry-run --verbose

Disable email: python alert_engine.py --no-email

---

## 🔒 Security

Do NOT upload:
- `.env`
- Service account JSON file
