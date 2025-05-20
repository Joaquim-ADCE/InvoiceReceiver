# src/core/invoice_validation.py
import pandas as pd
from config.navision_api import get_vendor_history, get_purchase_headers

def check_if_invoices_are_registered(
    qr_data_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Now checks both historic and live headers for any QR invoice (column 'G')
    that’s already in NAVISION, and returns
      (new_invoices_df, duplicate_invoices_df)
    """
    if "G" not in qr_data_df.columns:
        raise ValueError("Column 'G' (Vendor_Invoice_No) is required in QR data.")

    # historic
    hist = get_vendor_history()
    hist_nos = set(hist["Vendor_Invoice_No"].astype(str).values)

    # live headers
    hdr = get_purchase_headers()
    hdr_nos = set(hdr["Vendor_Invoice_No"].astype(str).values)

    qr = qr_data_df.copy()
    qr["_in_hist"]   = qr["G"].astype(str).isin(hist_nos)
    qr["_in_header"] = qr["G"].astype(str).isin(hdr_nos)

    qr["_already_registered"] = qr["_in_hist"] | qr["_in_header"]

    new_df = qr[~qr["_already_registered"]].drop(
        columns=["_in_hist","_in_header","_already_registered"]
    )
    dup_df = qr[ qr["_already_registered"]].drop(
        columns=["_in_hist","_in_header","_already_registered"]
    )

    return new_df, dup_df
