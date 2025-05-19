import os
import csv
from datetime import datetime
from pathlib import Path

# Path to the CSV log file; can be overridden via .env
LOG_FILE = Path(os.getenv("INVOICE_LOG_PATH", "logs/invoice_log.csv"))


def init_log():
    """
    Ensure the log directory and file exist, and create header row if missing.
    """
    # Create parent directory if needed
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Write header if file doesn't exist
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",          # ISO UTC timestamp
                "document_no",        # Navision document number
                "vendor_no",          # Vendor number
                "vendor_invoice_no",  # Invoice number from vendor
                "status",             # SUCCESS or FAILURE
                "error"               # Error message if any
            ])


def log_invoice(
    document_no: str,
    vendor_no: str,
    vendor_invoice_no: str,
    status: str,
    error: str = ""
):
    """
    Append an invoice processing entry to the CSV log.

    Args:
        document_no: Navision-assigned document number (or placeholder)
        vendor_no:   Buy_from_Vendor_No value
        vendor_invoice_no: Vendor_Invoice_No
        status:      "SUCCESS" or "FAILURE"
        error:       Optional error message if status is FAILURE
    """
    # Ensure log file exists with header
    init_log()

    timestamp = datetime.utcnow().isoformat()
    row = [timestamp, document_no, vendor_no, vendor_invoice_no, status, error]

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)
