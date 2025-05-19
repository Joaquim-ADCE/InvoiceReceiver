import pandas as pd


def parse_qr_to_dataframe(qr_string: str) -> pd.DataFrame:
    """
    Parse a QR-code string into a DataFrame with all required fields:
      - A: Vendor number
      - F: Document date
      - G: Vendor invoice number
      - I2, J2, K2: Base amount VAT 0%
      - I3, J3, K3: Base amounts VAT 6%, 5%, 4%
      - I4, J4, K4: VAT reduced amounts for I/J/K respectively
      - I5, J5, K5: Base amounts VAT 13%, 12%, 9%
      - I6, J6, K6: VAT intermediate amounts for I/J/K respectively
      - I7, J7, K7: Base amounts VAT 23%, 22%, 16%
      - I8, J8, K8: VAT normal amounts for I/J/K respectively

    Returns:
        pd.DataFrame with one row containing all columns, empty string if missing.
    """
    # Split raw QR string into key:value parts
    parts = qr_string.split("*")
    data = {}
    for part in parts:
        if ":" in part:
            key, value = part.split(":", 1)
            data[key.strip()] = value.strip()

    # Define expected columns
    cols = ["A", "F", "G"]
    for row in range(2, 9):
        for col in ["I", "J", "K"]:
            cols.append(f"{col}{row}")

    # Build a single row dict; missing keys default to empty string
    row = {col: data.get(col, "") for col in cols}
    return pd.DataFrame([row])
