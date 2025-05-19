# src/core/header_payload.py
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration: file to track last invoice number, prefix, and starting value
LAST_NO_FILE = Path(os.getenv("INVOICE_LAST_NO_PATH", "data/last_invoice_no.txt"))
INVOICE_PREFIX = os.getenv("INVOICE_PREFIX", "FCA")
# Default starting invoice number (e.g., FCA25000573)
INVOICE_START_NO = os.getenv("INVOICE_START_NO", f"{INVOICE_PREFIX}25000573")


def _ensure_last_no_file():
    """
    Ensure the tracking file exists, initializing it with INVOICE_START_NO if missing.
    """
    LAST_NO_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LAST_NO_FILE.exists():
        LAST_NO_FILE.write_text(INVOICE_START_NO)


def _get_last_no_int() -> int:
    """
    Read the last numeric part of the invoice number from the tracking file.
    """
    _ensure_last_no_file()
    content = LAST_NO_FILE.read_text().strip()
    match = re.match(rf"{INVOICE_PREFIX}(\d+)$", content)
    if not match:
        raise ValueError(f"Invalid invoice number in {LAST_NO_FILE}: {content}")
    return int(match.group(1))


def _save_no_int(num: int):
    """
    Save the given numeric part back to the tracking file (with prefix).
    """
    _ensure_last_no_file()
    LAST_NO_FILE.write_text(f"{INVOICE_PREFIX}{num}")


def generate_next_invoice_no() -> str:
    """
    Increment the last invoice number by 1, persist it, and return the full No string.

    Returns:
        e.g. "FCA25000574"
    """
    last_int = _get_last_no_int()
    next_int = last_int + 1
    _save_no_int(next_int)
    return f"{INVOICE_PREFIX}{next_int}"


def build_header_payload(
    buy_from_vendor_no: str,
    vendor_invoice_no: str,
    document_date: str
) -> Dict[str, str]:
    """
    Build the header payload for a single invoice.

    Args:
        buy_from_vendor_no: Vendor number (Buy_from_Vendor_No)
        vendor_invoice_no:  Invoice number from QR code (Vendor_Invoice_No)
        document_date:      Document date from QR code, e.g., 'YYYYMMDD' or ISO string

    Returns:
        Dict suitable for post_invoice_header(), with ISO dates and posting date as today.
    """
    invoice_no = generate_next_invoice_no()

    # Normalize document_date to ISO 8601 (YYYY-MM-DD)
    iso_doc_date = document_date
    if re.fullmatch(r"\d{8}", document_date):
        dt = datetime.strptime(document_date, "%Y%m%d")
        iso_doc_date = dt.strftime("%Y-%m-%d")

    # Posting date is always today's date
    posting_date = datetime.now().strftime("%Y-%m-%d")

    return {
        "No": invoice_no,
        "Buy_from_Vendor_No": buy_from_vendor_no,
        "Vendor_Invoice_No": vendor_invoice_no,
        "Document_Date": iso_doc_date,
        "Posting_Date": posting_date
    }
