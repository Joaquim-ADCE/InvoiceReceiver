import os
import requests
from typing import List, Dict
from dotenv import load_dotenv
import logging

load_dotenv()

NAVISION_BASE_URL = os.getenv("NAVISION_BASE_URL")  # e.g., http://srv004.adc.local:7048/BC140/ODataV4/Company('ADC')
NAVISION_USER = os.getenv("NAVISION_USERNAME")       # e.g., joaquima
NAVISION_WS_KEY = os.getenv("NAVISION_WS_KEY")       # long alphanumeric string
VENDORS_ENDPOINT = f"{NAVISION_BASE_URL}/Fornecedores_Table"

def get_navision_vendors() -> List[Dict]:
    """
    Fetch vendor data from NAVISION using basic auth and Web Services Key.
    """
    try:
        response = requests.get(
            VENDORS_ENDPOINT,
            auth=(NAVISION_USER, NAVISION_WS_KEY),
            headers={"Accept": "application/json"},
            verify=False  # Disable if using HTTP
        )
        response.raise_for_status()
        return response.json().get("value", [])
    except requests.RequestException as e:
        logging.error(f"Error fetching vendors: {e}")
        return []
