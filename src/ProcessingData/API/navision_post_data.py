import requests
from requests_ntlm import HttpNtlmAuth
import pandas as pd
import logging


API_URL_HEADER = "http://SRV004.ADC.local:7048/BC140/ODataV4/Company('ADC')/Fatura_Compra"
API_URL_LINE = "http://SRV004.ADC.local:7048/BC140/ODataV4/Company('ADC')/Linhas_Fatura_Compra"
USERNAME = "joaquima"
PASSWORD = "ItDep@AdCE2025"


def send_header_df_to_navision(header_df):
    """This function sends the header DataFrame to the Navision API
    Args:
        header_df (pd.DataFrame): DataFrame containing the header data
    """
    for _, header_row in header_df.iterrows():
        header_payload = {
            "Document_Type": str(header_row["Document Type"]),
            "No": str(header_row["No_"]),
            "Buy_from_Vendor_No": str(header_row["Buy-from Vendor No_"]),
            "Document_Date": header_row["Document Date"].strftime("%Y-%m-%d"),
            "Vendor_Invoice_No": str(header_row["Vendor Invoice No_"])
        }

        header_payload = {k: v for k, v in header_payload.items() if v}

        try:
            header_response = send_header_to_navision(header_payload)
            logging.info(f"Header sent successfully: {header_row['No_']}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending header {header_row['No_']}: {str(e)}")
            raise


def send_line_df_to_navision(line_df):
    """This function sends the line DataFrame to the Navision API
    Args:
        line_df (pd.DataFrame): DataFrame containing the line data
    """
    for _, line_row in line_df.iterrows():
        line_payload = {
            "Document_Type": str(line_row["Document Type"]),
            "Document_No": str(line_row["Document_No"]),
            "Line_No": int(line_row["Line_No"]),
            "Quantity": float(line_row["Quantity"]),
            "Direct_Unit_Cost": float(line_row["Direct_Unit_Cost"]),
            "Total_VAT_Amount": float(line_row["Total_VAT_Amount"]),
        }

        line_payload = {k: v for k, v in line_payload.items() if v}

        try:
            line_response = send_line_to_navision(line_payload)
            logging.info(f"Line sent successfully: {line_row['Document_No']} - {line_row['Line_No']}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending line {line_row['Document_No']} - {line_row['Line_No']}: {str(e)}")
            raise


def send_header_to_navision(payload):
    """This function sends the header data to the Navision API

    Args:
        payload (dict): Header data to be sent
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    response = requests.post(
        API_URL_HEADER,
        json=payload,
        headers=headers,
        auth=HttpNtlmAuth(USERNAME, PASSWORD),
        verify=False
    )
    response.raise_for_status()
    return response


def send_line_to_navision(payload):
    """This function sends the line data to the Navision API

    Args:
        payload (dict): Line data to be sent
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    response = requests.post(
        API_URL_LINE,
        json=payload,
        headers=headers,
        auth=HttpNtlmAuth(USERNAME, PASSWORD),
        verify=False
    )
    response.raise_for_status()
    return response
