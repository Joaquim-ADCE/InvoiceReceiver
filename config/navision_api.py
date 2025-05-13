import os
import requests
from requests_ntlm import HttpNtlmAuth
from typing import List, Dict
from dotenv import load_dotenv
import logging

load_dotenv()

def get_navision_vendors():
    """Fetch vendors from Navision using NTLM authentication."""
    try:
        # Get credentials from environment variables
        base_url = os.getenv('NAVISION_BASE_URL')
        username = os.getenv('NAVISION_USERNAME')
        domain = os.getenv('NAVISION_DOMAIN')
        password = os.getenv('NAVISION_PASSWORD')

        print(f"Connecting to Navision at {base_url}")
        print(f"Using credentials: {domain}\\{username}")

        # Create session with NTLM authentication
        session = requests.Session()
        session.auth = HttpNtlmAuth(f"{domain}\\{username}", password)
        
        # Make the request
        url = f"{base_url}/Ficha_Fornecedor"
        print(f"Requesting URL: {url}")
        
        response = session.get(url, verify=False)  # verify=False for self-signed certs
        
        if response.status_code != 200:
            print(f"Error response: {response.status_code}")
            print(f"Response content: {response.text}")
            response.raise_for_status()
        
        # Parse response
        data = response.json()
        vendors = data.get('value', [])
        print(f"Successfully fetched {len(vendors)} vendors")
        return vendors

    except Exception as e:
        print(f"Failed to fetch vendors from NAVISION: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def get_registered_invoices() -> list[str]:
    """Fetch already registered invoice numbers from NAVISION."""
    try:
        base_url = os.getenv('NAVISION_BASE_URL')
        username = os.getenv('NAVISION_USERNAME')
        domain = os.getenv('NAVISION_DOMAIN')
        password = os.getenv('NAVISION_PASSWORD')

        session = requests.Session()
        session.auth = HttpNtlmAuth(f"{domain}\\{username}", password)

        url = f"{base_url}/Faturas_Compra_Regist"
        print(f"Fetching registered invoices from: {url}")

        response = session.get(url, verify=False)
        response.raise_for_status()

        data = response.json().get("value", [])
        return [item["Vendor_Invoice_No"].strip() for item in data if "Vendor_Invoice_No" in item]
    except Exception as e:
        print(f"Error fetching registered invoices: {e}")
        return []
