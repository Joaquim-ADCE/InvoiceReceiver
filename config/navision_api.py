import os
import requests
import logging
import pandas as pd
from typing import List, Dict, Optional
from requests_ntlm import HttpNtlmAuth
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)


def _get_ntlm_session() -> requests.Session:
    """Create an NTLM-authenticated session."""
    session = requests.Session()
    session.auth = HttpNtlmAuth(
        f"{os.getenv('NAVISION_DOMAIN')}\\{os.getenv('NAVISION_USERNAME')}",
        os.getenv('NAVISION_PASSWORD')
    )
    return session


def _build_navision_url(endpoint: str) -> str:
    """Construct the full NAVISION OData URL for a given entity set."""
    return f"{os.getenv('NAVISION_BASE_URL')}/{endpoint}"


def _fetch_data(endpoint: str) -> Optional[List[Dict]]:
    """Fetch and parse data from a NAVISION OData endpoint."""
    try:
        session = _get_ntlm_session()
        url = _build_navision_url(endpoint)
        response = session.get(url, verify=False)
        response.raise_for_status()
        return response.json().get("value", [])
    except Exception as e:
        logging.error(f"❌ Error fetching data from {endpoint}: {e}")
        return None


def _post_data(endpoint: str, payload: Dict) -> Optional[Dict]:
    """
    Post a JSON payload to a NAVISION OData endpoint.
    Returns the created record as a dict (including server-assigned keys), or None on error.
    """
    try:
        session = _get_ntlm_session()
        url = _build_navision_url(endpoint)
        response = session.post(url, json=payload, verify=False)
        response.raise_for_status()
        logging.info(f"✅ Successfully posted to {endpoint}: {payload}")
        return response.json()
    except Exception as e:
        logging.error(f"❌ Error posting to {endpoint}: {e}")
        return None


# ─── public GET helpers (unchanged) ───────────────────────────────────────────

def get_navision_vendors() -> List[Dict]:
    """Fetch all vendors."""
    try:
        session = _get_ntlm_session()
        url = _build_navision_url("Ficha_Fornecedor")
        resp = session.get(url, verify=False); resp.raise_for_status()
        vendors = resp.json().get("value", [])
        logging.info(f"✅ Retrieved {len(vendors)} vendors.")
        return vendors
    except Exception as e:
        logging.error(f"❌ Failed to fetch vendors: {e}")
        return []


def get_gl_accounts() -> pd.DataFrame:
    """Fetch the C/G (GL) account list."""
    data = _fetch_data("Contas_C_G")
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_registered_invoice_lines() -> pd.DataFrame:
    """Fetch already registered invoice lines."""
    data = _fetch_data("Linhas_Compras_registadas")
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_registered_invoice_headers() -> pd.DataFrame:
    """Fetch already registered invoice headers."""
    data = _fetch_data("Faturas_Compra_Regist")
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_vendor_history() -> pd.DataFrame:
    """
    Returns a cleaned invoice history with key fields:
    Document_No, Buy_from_Vendor_No, No_line (as invoice ID), Description, Vendor_Invoice_No, Line_Amount.
    """
    headers = get_registered_invoice_headers()
    lines   = get_registered_invoice_lines()
    joined = pd.merge(
        lines, headers,
        how="left",
        left_on="Document_No",
        right_on="No",
        suffixes=("_line", "_header")
    )
    joined.reset_index(drop=True, inplace=True)
    joined["No"] = joined["No_line"]
    required_columns = [
        "Document_No", "Buy_from_Vendor_No", "No_line",
        "Description", "Vendor_Invoice_No", "Line_Amount"
    ]
    cleaned_df = joined[required_columns].copy()
    logging.info(f"✅ Vendor history: {len(cleaned_df)} records with selected columns.")
    return cleaned_df


# ─── public POST helpers ──────────────────────────────────────────────────────

def post_invoice_header(header_data: Dict) -> Optional[Dict]:
    """
    Post an invoice header to Navision.
    header_data must include the vendor-related fields, e.g.:
      {
        "Buy_from_Vendor_No": "VEND001",
        "Vendor_Invoice_No":  "INV-2025-001",
        "Document_Date":      "2025-05-18T00:00:00Z",
        "Posting_Date":       "2025-05-18T00:00:00Z",
        // ...any other required header properties
      }
    """
    return _post_data("Faturaca_Compra_Header", header_data)


def post_invoice_line(line_data: Dict) -> Optional[Dict]:
    """
    Post a single invoice line to Navision.
    line_data must include at least:
      {
        "Document_No":     "<Document_No from header>",
        "Account_No":      "CG-12345",
        "Line_Amount":     1500.00,
        // ...any other required line properties (Description, etc.)
      }
    """
    return _post_data("Linhas_Fatura_Compra", line_data)


def post_invoice_lines(lines_data: List[Dict]) -> List[Optional[Dict]]:
    """
    Helper to post multiple invoice lines in sequence.
    Returns a list of Navision’s responses (or None on failure per line).
    """
    results: List[Optional[Dict]] = []
    for line in lines_data:
        results.append(post_invoice_line(line))
    return results
