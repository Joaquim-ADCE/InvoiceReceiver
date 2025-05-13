import os
import sys
from pathlib import Path
import pandas as pd
import base64

print("Starting test script...")

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)
print(f"Added {project_root} to Python path")

try:
    print("Attempting to import required modules...")
    from config.graph_api import GraphClient
    from src.core.pdf_reader import extract_text_from_pdf_bytes
    from src.core.qr_reader import extract_qr_from_pdf_bytes
    from src.core.vendor_validation import validate_vendors_by_nif
    from src.core.invoice_validation import check_if_invoices_are_registered
    print("Successfully imported all modules")

    def parse_qr_to_dataframe(qr_string: str) -> pd.DataFrame:
        """Parses QR string into DataFrame with columns A (NIF) and G (Invoice)."""
        try:
            parts = qr_string.split("*")
            fields = dict(part.split(":", 1) for part in parts if ":" in part)
            nif = fields.get("A", "").strip()
            inv = fields.get("G", "").strip()
            if not nif or not inv:
                return pd.DataFrame()
            return pd.DataFrame([{"A": nif, "G": inv}])
        except Exception as e:
            print(f"Failed to parse QR: {e}")
            return pd.DataFrame()

    def test_email_pdf_fetch():
        print("\nStarting email PDF fetch test...")
        try:
            client = GraphClient()
            print("Fetching emails from ngomes@adcecija.pt...")
            emails = client.get_all_emails_from("ngomes@adcecija.pt")
            
            if not emails:
                print("No emails found from ngomes@adcecija.pt!")
                return

            all_qr_data = []
            for email in emails:
                subject = email.get("subject", "[No Subject]")
                print(f"\nProcessing email: {subject}")
                
                attachments = email.get("attachments", [])
                pdfs = [att for att in attachments if att.get("contentType") == "application/pdf"]
                
                for pdf in pdfs:
                    print(f"\nProcessing PDF: {pdf.get('name')}")
                    content_bytes = base64.b64decode(pdf["contentBytes"])
                    qr = extract_qr_from_pdf_bytes(content_bytes)
                    
                    if qr:
                        print(f"Found QR code: {qr}")
                        df = parse_qr_to_dataframe(qr)
                        if not df.empty:
                            df["Email Subject"] = subject
                            df["PDF Name"] = pdf.get("name", "Unnamed.pdf")
                            all_qr_data.append(df)

            if not all_qr_data:
                print("No QR data found in any PDFs!")
                return

            # Combine all QR data
            all_qr_df = pd.concat(all_qr_data, ignore_index=True)
            
            # First validate vendors
            valid_vendors_df, invalid_vendors_df = validate_vendors_by_nif(all_qr_df)
            
            # Then check for duplicate invoices in valid vendors
            if not valid_vendors_df.empty:
                new_invoices_df, duplicate_invoices_df = check_if_invoices_are_registered(valid_vendors_df)
            else:
                new_invoices_df = pd.DataFrame()
                duplicate_invoices_df = pd.DataFrame()

            print("\n📊 Results:")
            print(f"\nInvalid vendors: {len(invalid_vendors_df)}")
            if not invalid_vendors_df.empty:
                print(invalid_vendors_df)
                
            print(f"\nDuplicate invoices: {len(duplicate_invoices_df)}")
            if not duplicate_invoices_df.empty:
                print(duplicate_invoices_df)
                
            print(f"\nNew invoices to process: {len(new_invoices_df)}")
            if not new_invoices_df.empty:
                print(new_invoices_df)

            # Save results
            invalid_vendors_df.to_csv("invalid_vendors.csv", index=False)
            duplicate_invoices_df.to_csv("duplicate_invoices.csv", index=False)
            new_invoices_df.to_csv("new_invoices.csv", index=False)

            return invalid_vendors_df, duplicate_invoices_df, new_invoices_df

        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()

    if __name__ == "__main__":
        print("\nRunning test as main...")
        test_email_pdf_fetch()
        print("Test completed.")

except Exception as e:
    print(f"❌ Failed during setup: {str(e)}")
    import traceback
    traceback.print_exc()
