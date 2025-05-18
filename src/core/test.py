# === Revised test.py ===

import os
import sys
import base64
from pathlib import Path

# Setup - Move this BEFORE any project imports
project_root = str(Path(__file__).parent.parent.parent.absolute())  # Changed to include one more parent
sys.path.insert(0, project_root)

# Now we can import project modules
import pandas as pd
from dotenv import load_dotenv
from config.graph_api import GraphClient
from src.core.qr_reader import extract_qr_from_pdf_bytes
from src.core.vendor_validation import validate_vendors_by_nif
from src.core.invoice_validation import check_if_invoices_are_registered
from src.core.openai_client import suggest_gl_account_from_pdf

# Utilities
def parse_qr_to_dataframe(qr_string: str) -> pd.DataFrame:
    try:
        parts = qr_string.split("*")
        fields = dict(part.split(":", 1) for part in parts if ":" in part)
        return pd.DataFrame([{"A": fields.get("A", "").strip(), "G": fields.get("G", "").strip()}])
    except Exception as e:
        print(f"Failed to parse QR: {e}")
        return pd.DataFrame()

def clean_pycache():
    import shutil
    for root, dirs, files in os.walk(project_root):
        for d in dirs:
            if d == "__pycache__":
                full_path = os.path.join(root, d)
                shutil.rmtree(full_path)
                print(f"🩹 Removed cache: {full_path}")

# Main Function
def test_email_pdf_fetch_and_classify():
    print("\n📩 Fetching emails...")
    client = GraphClient()
    emails = client.get_all_emails_from("ngomes@adcecija.pt")

    all_qr_data = []
    pdf_mapping = []

    for email in emails:
        subject = email.get("subject", "[No Subject]")
        sender = email.get("from", {}).get("emailAddress", {}).get("name", "Unknown")
        pdfs = [att for att in email.get("attachments", []) if att.get("contentType") == "application/pdf"]

        for pdf in pdfs:
            content_bytes = base64.b64decode(pdf["contentBytes"])
            qr = extract_qr_from_pdf_bytes(content_bytes)

            if qr:
                df = parse_qr_to_dataframe(qr)
                if not df.empty:
                    df["Email Subject"] = subject
                    df["PDF Name"] = pdf.get("name", "Unnamed.pdf")
                    all_qr_data.append(df)

                    pdf_mapping.append({
                        "pdfs": [{
                            "filename": pdf.get("name", "Unnamed.pdf"),
                            "content": content_bytes
                        }]
                    })

    if not all_qr_data:
        print("❌ No QR data found.")
        return

    all_qr_df = pd.concat(all_qr_data, ignore_index=True)

    # Step 1: Vendor Validation
    print("\n1⃣ Validating vendors against NAVISION...")
    valid_vendors_df, invalid_vendors_df = validate_vendors_by_nif(all_qr_df)

    print(f"✅ Valid vendors: {len(valid_vendors_df)}")
    print(f"❌ Invalid vendors: {len(invalid_vendors_df)}")

    # Step 2: Check for duplicate invoices
    print("\n2⃣ Checking for duplicate invoices...")
    if not valid_vendors_df.empty:
        new_invoices_df, duplicate_invoices_df = check_if_invoices_are_registered(valid_vendors_df)

        new_invoices_df = new_invoices_df.drop(columns=["vendor_no"], errors="ignore")
        new_invoices_df = new_invoices_df.merge(
            valid_vendors_df[["A", "vendor_no"]],
            on="A",
            how="left"
        )
    else:
        new_invoices_df = pd.DataFrame()
        duplicate_invoices_df = pd.DataFrame()

    # Step 3: GPT Suggestions for GL Accounts
    print("\n🧐 Asking GPT for GL account suggestions...")
    gl_suggestions = []

    for i, invoice in new_invoices_df.iterrows():
        vendor_nif = invoice["A"]
        invoice_no = invoice["G"]
        vendor_no = invoice.get("vendor_no")

        if pd.isna(vendor_no):
            print(f"⚠️ No vendor_no found for NIF {vendor_nif}. Skipping.")
            continue

        email_meta = pdf_mapping[i] if i < len(pdf_mapping) else {}
        try:
            suggestion = suggest_gl_account_from_pdf(email_meta, vendor_no)
        except Exception as e:
            print(f"❌ GPT failed for invoice {invoice_no} from vendor {vendor_no}: {e}")
            suggestion = "❗ GPT call error"

        gl_suggestions.append({
            "vendor_nif": vendor_nif,
            "vendor_no": vendor_no,
            "invoice_no": invoice_no,
            "suggested_gl": suggestion
        })

    suggestions_df = pd.DataFrame(gl_suggestions)
    suggestions_df.to_csv("gl_suggestions.csv", index=False)

    # Save results
    print("\n✅ Results Summary:")
    print(f"- Invalid vendors: {len(invalid_vendors_df)}")
    print(f"- Duplicate invoices: {len(duplicate_invoices_df)}")
    print(f"- New invoices to process: {len(new_invoices_df)}")

    invalid_vendors_df.to_csv("invalid_vendors.csv", index=False)
    duplicate_invoices_df.to_csv("duplicate_invoices.csv", index=False)
    new_invoices_df.to_csv("new_invoices.csv", index=False)

    print("\n📁 All outputs saved.")

    print("\n🧼 Cleaning up __pycache__...")
    clean_pycache()

if __name__ == "__main__":
    test_email_pdf_fetch_and_classify()


# === End of test.py ===
