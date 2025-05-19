import os
import csv
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Graph API client for authentication
from config.graph_api import GraphClient

# Load environment variables
load_dotenv()

# Paths and configuration
LOG_FILE = Path(os.getenv("INVOICE_LOG_PATH", "logs/invoice_log.csv"))
REPORT_RECIPIENTS = os.getenv("REPORT_RECIPIENTS", "").split(",")
PDF_SENDER_EMAIL = os.getenv("PDF_SENDER_EMAIL")


def generate_report(period_days: int = 1):
    """
    Read the CSV log and return entries from the last `period_days` days.
    Returns (rows_list, error_message). If no entries or file missing, rows_list is None.
    """
    cutoff = datetime.utcnow() - timedelta(days=period_days)
    if not LOG_FILE.exists():
        return None, "Log file does not exist."

    rows = []
    with open(LOG_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = datetime.fromisoformat(row.get("timestamp", ""))
            except ValueError:
                continue
            if ts >= cutoff:
                rows.append(row)

    if not rows:
        return None, "No log entries in the specified period."

    return rows, None


def send_report(period_days: int = 1):
    """
    Generate a summary report for the last `period_days` days and send it via Microsoft Graph.
    """
    rows, error = generate_report(period_days)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    # Build report content
    if error:
        html_body = f"<p>No entries to report: {error}</p>"
    else:
        total = len(rows)
        success_count = sum(1 for r in rows if r.get("status") == "SUCCESS")
        failures = [r for r in rows if r.get("status") != "SUCCESS"]
        error_counts = {}
        for r in failures:
            err = r.get("error", "").strip() or "Erro desconhecido"
            error_counts[err] = error_counts.get(err, 0) + 1

        lines = [
            "*Sistema de inserção de faturas de fornecedores*",  # plain text fallback
            f"O sistema tentou inserir hoje {total} PDFs enviados pelo e-mail {PDF_SENDER_EMAIL}, aqui está o relatório:",
            "<br>",
            f"- ✅ Inserções bem-sucedidas: {success_count}",
        ]
        for err_msg, cnt in error_counts.items():
            lines.append(f"- ⚠️ {err_msg}: {cnt}")

        if failures:
            lines.append("<br>")
            lines.append("PDFs com falha:")
            for r in failures:
                pdf_id = r.get("vendor_invoice_no") or r.get("document_no") or "<sem identificação>"
                err_msg = r.get("error", "").strip()
                lines.append(f"- {pdf_id} — {err_msg}")

        # Join lines into HTML
        html_body = '<br>'.join(lines)

    # Prepare Graph mail payload
    gc = GraphClient()
    recipients = [
        {"emailAddress": {"address": addr.strip()}}
        for addr in REPORT_RECIPIENTS if addr.strip()
    ]
    mail_payload = {
        "message": {
            "subject": f"Invoice Processing Report - {date_str}",
            "body": {"contentType": "html", "content": html_body},
            "toRecipients": recipients,
            "from": {"emailAddress": {"address": PDF_SENDER_EMAIL}}
        },
        "saveToSentItems": "true"
    }

    # Send via Graph endpoint
    url = f"https://graph.microsoft.com/v1.0/users/{PDF_SENDER_EMAIL}/sendMail"
    headers = gc._get_headers()
    response = requests.post(url, headers=headers, json=mail_payload)
    response.raise_for_status()

    return True
