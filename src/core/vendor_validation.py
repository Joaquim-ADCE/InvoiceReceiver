# src/core/vendor_validator.py

import pandas as pd
from config.navision_api import get_navision_vendors

def validate_vendors_by_nif(qr_data_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validates QR invoice data against NAVISION vendors based on NIF.

    Args:
        qr_data_df: DataFrame with at least a column 'A' (NIF from QR code)

    Returns:
        Tuple of two DataFrames:
            - valid_vendors_df: entries whose NIF exists in NAVISION
            - invalid_vendors_df: entries not found in NAVISION
    """
    vendors_raw = get_navision_vendors()
    if not vendors_raw:
        raise ValueError("Could not retrieve vendor data from NAVISION.")

    vendors_df = pd.DataFrame(vendors_raw)
    if "VAT_Registration_No" not in vendors_df.columns:
        raise ValueError("Missing 'VAT_Registration_No' in NAVISION vendor data.")

    qr_data_df = qr_data_df.copy()
    qr_data_df['A'] = qr_data_df['A'].astype(str).str.strip()
    vendors_df['VAT_Registration_No'] = vendors_df['VAT_Registration_No'].astype(str).str.strip()

    qr_data_df['exists_in_navision'] = qr_data_df['A'].isin(vendors_df['VAT_Registration_No'])

    valid_vendors_df = qr_data_df[qr_data_df['exists_in_navision']].drop(columns=['exists_in_navision'])
    invalid_vendors_df = qr_data_df[~qr_data_df['exists_in_navision']].drop(columns=['exists_in_navision'])

    return valid_vendors_df, invalid_vendors_df
