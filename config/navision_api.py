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
    """Construct the full NAVISION API URL."""
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

def get_navision_vendors() -> List[Dict]:
    """Fetch vendors using existing vendor endpoint."""
    try:
        session = _get_ntlm_session()
        url = _build_navision_url("Ficha_Fornecedor")
        response = session.get(url, verify=False)
        response.raise_for_status()
        data = response.json()
        vendors = data.get("value", [])
        logging.info(f"✅ Retrieved {len(vendors)} vendors.")
        return vendors
    except Exception as e:
        logging.error(f"❌ Failed to fetch vendors: {e}")
        return []

def get_gl_accounts() -> pd.DataFrame:
    """Fetch C/G (GL) account records."""
    data = _fetch_data("Contas_C_G")
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_registered_invoice_lines() -> pd.DataFrame:
    """Fetch registered invoice lines."""
    data = _fetch_data("Linhas_Compras_registadas")
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_registered_invoice_headers() -> pd.DataFrame:
    """Fetch registered invoice headers."""
    data = _fetch_data("Faturas_Compra_Regist")
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_vendor_history() -> pd.DataFrame:
    """
    Returns a cleaned invoice history with key fields:
    Document_No, Buy_from_Vendor_No, No_line (as invoice ID), and Description.
    """
    lines = get_registered_invoice_lines()
    headers = get_registered_invoice_headers()

    if lines.empty:
        logging.warning("⚠️ No invoice lines found.")
        return pd.DataFrame()

    if headers.empty:
        logging.warning("⚠️ No invoice headers found. Returning lines only.")
        return lines[["Document_No", "No_line"]]  # Minimal fallback

    joined = lines.merge(
        headers,
        how="left",
        left_on="Document_No",
        right_on="No",
        suffixes=("_line", "_header")
    )

    joined.reset_index(drop=True, inplace=True)
    joined["No"] = joined["No_line"]

    # Cleaned output
    required_columns = ["Document_No", "Buy_from_Vendor_No", "No_line", "Description", "Vendor_Invoice_No", "Line_Amount"]
    cleaned_df = joined[required_columns].copy()

    logging.info(f"✅ Vendor history: {len(cleaned_df)} records with selected columns.")
    return cleaned_df

