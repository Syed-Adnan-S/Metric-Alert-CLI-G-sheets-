import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
import logging
import uuid
import argparse
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# ---------- Logging Setup ----------

logging.basicConfig(
    filename="alerts.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ------------------------------

load_dotenv()

SERVICE_ACCOUNT_FILE = "metric_alerts_service_account.json"
SHEET_ID = os.environ["SHEET_ID"]

LATEST_TAB = "Latest"
CONFIG_TAB = "Config"
LOGS_TAB = "Logs"

EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = int(os.environ["EMAIL_PORT"])
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_APP_PASSWORD = os.environ["EMAIL_APP_PASSWORD"]
EMAIL_SENDER_NAME = os.environ.get("EMAIL_SENDER_NAME", "Metrics Bot")


# ---------- Helpers ----------

def parse_percent_display(s: str) -> float:
    s = str(s).strip()
    if s.endswith("%"):
        return float(s[:-1])
    return float(s)


def parse_bool(v):
    return str(v).strip().lower() in ("true", "1", "yes", "y")


def parse_recipients(s):
    return [e.strip() for e in str(s).split(",") if e.strip()]


def should_trigger(value_pct: float, threshold: float, direction: str) -> bool:
    direction = direction.strip().lower()

    if direction == "above":
        return value_pct >= threshold

    if direction == "below":
        return value_pct <= -threshold

    if direction == "abs":
        return abs(value_pct) >= threshold

    raise ValueError(f"Unknown direction: {direction}")


def send_email(to_list, subject, body_text, html_body):
    msg = EmailMessage()
    msg["From"] = f"{EMAIL_SENDER_NAME} <{EMAIL_USER}>"
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject

    # Plain text fallback
    msg.set_content(body_text)

    # HTML version
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_APP_PASSWORD)
        server.send_message(msg)


def append_email_log(ws_logs, row_values: list[str]):
    """
    Appends one row to Logs sheet.
    """
    ws_logs.append_row(row_values, value_input_option="USER_ENTERED")


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Google Sheets metric alert system (MoM/YoY rules -> email + sheet logs)."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do everything except sending emails and writing sheet logs. Prints what would happen."
    )

    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Do not send emails (but still write logs to the Logs tab unless --no-sheet-log is set)."
    )

    parser.add_argument(
        "--no-sheet-log",
        action="store_true",
        help="Do not write to the Logs tab (still sends emails unless --no-email/--dry-run)."
    )

    parser.add_argument(
        "--latest-tab",
        default=LATEST_TAB,
        help=f"Name of the Latest tab (default: {LATEST_TAB})"
    )

    parser.add_argument(
        "--config-tab",
        default=CONFIG_TAB,
        help=f"Name of the Config tab (default: {CONFIG_TAB})"
    )

    parser.add_argument(
        "--logs-tab",
        default=LOGS_TAB,
        help=f"Name of the Logs tab (default: {LOGS_TAB})"
    )

    parser.add_argument(
        "--subject-prefix",
        default="[Metric Alert]",
        help="Prefix for email subject."
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra debug information to terminal."
    )

    return parser


# ---------- Main ----------

def main(args):
    logging.info("Script execution started")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    gc = gspread.authorize(creds)

    sh = gc.open_by_key(SHEET_ID)
    
    ws_latest = sh.worksheet(args.latest_tab)
    ws_config = sh.worksheet(args.config_tab)

    ws_logs = None
    if not args.dry_run and not args.no_sheet_log:
        ws_logs = sh.worksheet(args.logs_tab)
    
    run_id = str(uuid.uuid4())

    latest_values = ws_latest.get_all_values()
    config_values = ws_config.get_all_values()

    latest_headers = latest_values[0]
    latest_rows = latest_values[1:]

    config_headers = config_values[0]
    config_rows = config_values[1:]

    # Latest: list[dict]
    latest_data = [dict(zip(latest_headers, r)) for r in latest_rows if any(cell.strip() for cell in r)]
    latest_by_metric = {row["Metric"]: row for row in latest_data if row.get("Metric")}

    triggered_alerts = []

    for r in config_rows:
        config = dict(zip(config_headers, r))

        if not parse_bool(config.get("Enabled", "")):
            continue

        metric = config.get("Metric", "").strip()
        check_col = config.get("Check", "").strip()
        direction = config.get("Direction", "").strip()
        recipients = parse_recipients(config.get("Recipients", ""))

        # Your config header is "Threshold Pct"
        threshold_str = config.get("Threshold Pct", "").strip()

        if not metric or not check_col or not direction or not recipients or not threshold_str:
            continue

        if metric not in latest_by_metric:
            continue

        try:
            threshold = float(threshold_str)
        except ValueError:
            continue

        latest_row = latest_by_metric[metric]

        if check_col not in latest_row:
            # Column name mismatch (ex: "v MoM" vs "v MoM ")
            continue

        raw_value = latest_row.get(check_col, "")
        try:
            value_pct = parse_percent_display(raw_value)
        except ValueError:
            continue

        if should_trigger(value_pct, threshold, direction):
            triggered_alerts.append({
                "metric": metric,
                "check": check_col,
                "value_pct": value_pct,
                "threshold": threshold,
                "direction": direction,
                "recipients": recipients,
                "month": latest_row.get("Current Month", ""),
                "current_value": latest_row.get("Current Month Value", ""),
            })

    if not triggered_alerts:
        logging.info("No alerts triggered in this run")
        print("No alerts triggered.")
        return

    # Group alerts by recipient so each person gets ONE email with all relevant triggers
    grouped = {}
    for a in triggered_alerts:
        for recipient in a["recipients"]:
            grouped.setdefault(recipient, []).append(a)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for recipient, items in grouped.items():
        recipients = [recipient]

        subject = f"{args.subject_prefix} {len(items)} trigger(s) detected"
        lines = []
        lines.append(f"Triggered at: {now_str}")
        lines.append("")
        lines.append("The following metric checks exceeded thresholds:")
        lines.append("")

        for a in items:
            lines.append(
                f"- {a['metric']} ({a['month']}): {a['check']} = {a['value_pct']:.2f}% "
                f"(rule: {a['direction']} {a['threshold']:.2f}%), Current Value = {a['current_value']}"
            )

        body_text = "\n".join(lines)

        # ---------- Build HTML Body ----------

        html_lines = [
            "<h2 style='font-family:Arial;'>📊 Metric Alert</h2>",
            f"<p><strong>Triggered at:</strong> {now_str}</p>",
            "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; font-family:Arial;'>",
            "<tr style='background-color:#f2f2f2;'>"
            "<th>Metric</th>"
            "<th>Month</th>"
            "<th>Check</th>"
            "<th>Value</th>"
            "<th>Rule</th>"
            "</tr>"
        ]

        for a in items:
            color = "red" if a["value_pct"] < 0 else "green"

            html_lines.append(
                "<tr>"
                f"<td>{a['metric']}</td>"
                f"<td>{a['month']}</td>"
                f"<td>{a['check']}</td>"
                f"<td style='color:{color}; font-weight:bold;'>"
                f"{a['value_pct']:.2f}%</td>"
                f"<td>{a['direction']} {a['threshold']:.2f}%</td>"
                "</tr>"
            )

        html_lines.append("</table>")

        html_body = "\n".join(html_lines)

        # ---------- Handle CLI Modes ----------

        if args.dry_run:
            print("\n--- DRY RUN ---")
            print(f"Would email: {recipients}")
            print(f"Subject: {subject}")
            print(body_text)
            print("--- END DRY RUN ---\n")
            logging.info(f"[DRY RUN] Would have emailed: {recipients}")
            continue

        if args.no_email:
            logging.info(f"[NO EMAIL] Email sending disabled. Would have emailed: {recipients}")
            if args.verbose:
                print(f"[NO EMAIL] Would have emailed: {recipients}")
        else:
            try:
                send_email(recipients, subject, body_text, html_body)
                logging.info(f"Email successfully sent to {recipients}")
            except Exception:
                logging.exception(f"Failed to send email to {recipients}")
                continue


        timestamp = datetime.now().isoformat(timespec="seconds")

        # Build a compact triggers summary
        trigger_summaries = []
        for a in items:
            trigger_summaries.append(
                f"{a['metric']} {a['check']}={a['value_pct']:.2f}% "
                f"(rule: {a['direction']} {a['threshold']:.2f}%)"
            )

        triggers_text = "; ".join(trigger_summaries)

        log_row = [
            timestamp,                              # Timestamp
            run_id,                                 # Run ID
            ", ".join(recipients),                  # To
            subject,                                # Subject
            str(len(items)),                        # Trigger Count
            triggers_text,                          # Triggers
            body_text,                                   # Email Body (full)
            SHEET_ID,                               # Sheet ID
            LATEST_TAB,                             # Latest Tab
            CONFIG_TAB                              # Config Tab
        ]

        if ws_logs is not None:
            try:
                append_email_log(ws_logs, log_row)
            except Exception:
                logging.exception("Failed to append log row to Google Sheet")
        else:
            if args.verbose:
                print("Sheet logging disabled.")


if __name__ == "__main__":
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        main(args)
    except Exception:
        logging.exception("Fatal error occurred during script execution")
        print("A fatal error occurred. Check alerts.log for details.")
