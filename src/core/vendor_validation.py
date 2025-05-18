import pandas as pd
from config.navision_api import get_navision_vendors

def validate_vendors_by_nif(qr_data_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validates QR invoice data against NAVISION vendors based on NIF.

    Args:
        qr_data_df: DataFrame with at least a column 'A' (NIF from QR code)

    Returns:
        Tuple of two DataFrames:
            - valid_vendors_df: entries whose NIF exists in NAVISION (with vendor 'No' added as 'vendor_no')
            - invalid_vendors_df: entries not found in NAVISION
    """
    vendors_raw = get_navision_vendors()
    if not vendors_raw:
        raise ValueError("Could not retrieve vendor data from NAVISION.")

    vendors_df = pd.DataFrame(vendors_raw)
    if "VAT_Registration_No" not in vendors_df.columns or "No" not in vendors_df.columns:
        raise ValueError("Missing expected columns in NAVISION vendor data.")

    # Clean both DataFrames
    qr_data_df = qr_data_df.copy()
    qr_data_df["A"] = qr_data_df["A"].astype(str).str.strip()
    vendors_df["VAT_Registration_No"] = vendors_df["VAT_Registration_No"].astype(str).str.strip()
    vendors_df["No"] = vendors_df["No"].astype(str).str.strip()

    # Perform merge to map Vendor No
    merged_df = qr_data_df.merge(
        vendors_df[["VAT_Registration_No", "No"]],
        left_on="A",
        right_on="VAT_Registration_No",
        how="left"
    )

    valid_vendors_df = merged_df[merged_df["No"].notna()].copy()
    valid_vendors_df = valid_vendors_df.rename(columns={"No": "vendor_no"}).drop(columns=["VAT_Registration_No"])

    invalid_vendors_df = merged_df[merged_df["No"].isna()].drop(columns=["VAT_Registration_No", "No"])

    return valid_vendors_df, invalid_vendors_df
