from typing import Dict, Optional


def build_line_payload(
    document_no: str,
    account_no: str,
    amount_excl: float,
    vat_amount: float,
    line_index: int = 1,
    vendor_no: Optional[str] = None,
    vat_prod_posting_group: Optional[str] = None
) -> Dict[str, object]:
    """
    Build the line payload for an invoice based on its header.

    Args:
        document_no:             Header invoice No (e.g., "FCA25000574")
        account_no:              GL account number recommendation
        amount_excl:             Base amount excluding VAT
        vat_amount:              VAT amount
        line_index:              Multiplier index for Line_No (10000 * index)
        vendor_no:               Vendor number from header; for withholding logic
        vat_prod_posting_group:  VAT Product Posting Group for this line

    Returns:
        Dict suitable for OData POST to purchase lines endpoint
    """
    # Line_No increments: 10000, 20000, etc.
    line_no = 10000 * line_index

    payload: Dict[str, object] = {
        "Document_Type": "Invoice",
        "Document_No": document_no,
        "Line_No": line_no,
        "Type": "G/L Account",
        "No": account_no,
        "Quantity": 1,
        "Direct_Unit_Cost": amount_excl,
        "Total_Amount_Excl_VAT": amount_excl
    }

    # Include VAT amount if present
    if vat_amount:
        payload["Total_VAT_Amount"] = vat_amount

    # Withholding tax for vendors not starting with 'F'
    if vendor_no and not vendor_no.startswith("F"):
        payload["Withholding_Tax_Code"] = "IRSIDENP23"

    # VAT Product Posting Group if provided
    if vat_prod_posting_group:
        payload["VAT_Prod_Posting_Group"] = vat_prod_posting_group

    return payload
