import pandas as pd
from config.navision_api import get_vendor_history

def check_if_invoices_are_registered(qr_data_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Checks if invoices in the DataFrame have already been registered in NAVISION.

    Args:
        qr_data_df (pd.DataFrame): DataFrame with at least column 'G' (Vendor_Invoice_No from QR code)

    Returns:
        Tuple of two DataFrames:
            - new_invoices_df: not found in NAVISION
            - duplicate_invoices_df: already registered in NAVISION
    """
    if "G" not in qr_data_df.columns:
        raise ValueError("Column 'G' (Vendor_Invoice_No) is required in QR data.")

    registered_invoices_df = get_vendor_history()
    registered_invoice_nos = set(registered_invoices_df['Vendor_Invoice_No'].values)

    qr_data_df = qr_data_df.copy()
    qr_data_df["already_registered"] = qr_data_df["G"].isin(registered_invoice_nos)

    new_invoices_df = qr_data_df[~qr_data_df["already_registered"]].drop(columns=["already_registered"])
    duplicate_invoices_df = qr_data_df[qr_data_df["already_registered"]].drop(columns=["already_registered"])

    return new_invoices_df, duplicate_invoices_df