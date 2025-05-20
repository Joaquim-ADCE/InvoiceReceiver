# config/navision_api.py
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
    session = requests.Session()
    session.auth = HttpNtlmAuth(
        f"{os.getenv('NAVISION_DOMAIN')}\\{os.getenv('NAVISION_USERNAME')}",
        os.getenv('NAVISION_PASSWORD')
    )
    return session

def _build_navision_url(endpoint: str) -> str:
    return f"{os.getenv('NAVISION_BASE_URL')}/{endpoint}"

def _fetch_data(endpoint: str) -> Optional[List[Dict]]:
    try:
        sess = _get_ntlm_session()
        url = _build_navision_url(endpoint)
        r = sess.get(url, verify=False)
        r.raise_for_status()
        return r.json().get("value", [])
    except Exception as e:
        logging.error(f"❌ Error fetching data from {endpoint}: {e}")
        return None

def _post_data(endpoint: str, payload: Dict) -> Optional[Dict]:
    try:
        sess = _get_ntlm_session()
        url = _build_navision_url(endpoint)
        r = sess.post(url, json=payload, verify=False)
        r.raise_for_status()
        logging.info(f"✅ Successfully posted to {endpoint}: {payload}")
        return r.json()
    except Exception as e:
        logging.error(f"❌ Error posting to {endpoint}: {e}")
        return None

def get_navision_vendors() -> List[Dict]:
    try:
        sess = _get_ntlm_session()
        url = _build_navision_url("Ficha_Fornecedor")
        r = sess.get(url, verify=False); r.raise_for_status()
        v = r.json().get("value", [])
        logging.info(f"✅ Retrieved {len(v)} vendors.")
        return v
    except Exception as e:
        logging.error(f"❌ Failed to fetch vendors: {e}")
        return []

def get_gl_accounts() -> pd.DataFrame:
    data = _fetch_data("Contas_C_G")
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_registered_invoice_lines() -> pd.DataFrame:
    data = _fetch_data("Linhas_Compras_registadas")
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_registered_invoice_headers() -> pd.DataFrame:
    data = _fetch_data("Faturas_Compra_Regist")
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_purchase_headers() -> pd.DataFrame:
    """
    NEW: pull the live Purchase Header table so we can dedupe on
    Vendor_Invoice_No before trying to post again.
    """
    data = _fetch_data("Faturaca_Compra_Header")
    df = pd.DataFrame(data) if data else pd.DataFrame()
    logging.info(f"✅ Retrieved {len(df)} purchase headers.")
    return df

def get_vendor_history() -> pd.DataFrame:
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
    cols = [
        "Document_No", "Buy_from_Vendor_No", "No_line",
        "Description", "Vendor_Invoice_No", "Line_Amount"
    ]
    df = joined[cols].copy()
    logging.info(f"✅ Vendor history: {len(df)} records with selected columns.")
    return df

def post_invoice_header(header_data: Dict) -> Optional[Dict]:
    return _post_data("Faturaca_Compra_Header", header_data)

def post_invoice_line(line_data: Dict) -> Optional[Dict]:
    return _post_data("Linhas_Fatura_Compra", line_data)

def post_invoice_lines(lines_data: List[Dict]) -> List[Optional[Dict]]:
    results = []
    for ln in lines_data:
        results.append(post_invoice_line(ln))
    return results
