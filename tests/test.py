import os
import sys
from pathlib import Path
import base64
import pandas as pd
from typing import List, Dict

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import base64
from config.graph_api import GraphClient
from src.core.pdf_reader import extract_text_from_pdf_bytes
from src.core.qr_reader import extract_qr_from_pdf_bytes

def test_pdf_text_extraction_from_emails():
    """
    Test that connects to the email, fetches PDF attachments,
    and extracts text from them using the PDF reader.
    """
    graph = GraphClient()
    emails = graph.get_all_emails_from()

    found_pdf = False

    for email in emails:
        attachments = email.get("attachments", [])
        for att in attachments:
            if att.get("contentType") == "application/pdf":
                content_bytes = base64.b64decode(att["contentBytes"])
                extracted_text = extract_text_from_pdf_bytes(content_bytes)

                print(f"\n--- PDF: {att['name']} ---")
                print(extracted_text[:500])  # Show preview
                print("\n---------------------------\n")

                assert extracted_text.strip() != "", f"PDF '{att['name']}' is empty"
                found_pdf = True

    assert found_pdf, "No PDF attachments found in emails."

def test_email_pdf_fetch():
    try:
        print("Starting test...")
        client = GraphClient()
        
        # Store results for DataFrame
        results = []
        
        print("Attempting to fetch emails from ngomes@adcecija.pt...")
        emails = client.get_all_emails_from("ngomes@adcecija.pt")
        print(f"Received {len(emails)} emails from initial query")
        
        if not emails:
            print("✅ Connected, but no emails found from ngomes@adcecija.pt")
            print("Trying to fetch all emails with PDFs instead...")
            emails = client.get_all_emails()
            print(f"Received {len(emails)} emails from fallback query")

        # Filter for PDFs
        filtered = []
        for email in emails:
            attachments = email.get("attachments", [])
            pdfs = [
                att for att in attachments
                if att.get("contentType") == "application/pdf"
            ]
            if pdfs:
                filtered.append({
                    "email": email,
                    "pdf_attachments": pdfs
                })

        if not filtered:
            print("✅ Connected, but no emails with PDF attachments were found.")
            return

        print(f"✅ Fetched {len(filtered)} email(s) with PDF attachments:\n")
        for entry in filtered:
            email = entry["email"]
            subject = email.get("subject", "[No Subject]")
            sender = email.get("from", {}).get("emailAddress", {}).get("address", "Unknown")
            received_date = email.get("receivedDateTime", "Unknown")
            
            print(f"\n📨 Subject: {subject}")
            
            for pdf in entry["pdf_attachments"]:
                pdf_name = pdf.get("name", "Unnamed PDF")
                print(f"\n   📎 PDF: {pdf_name}")
                
                # Process PDF content
                content_bytes = base64.b64decode(pdf["contentBytes"])
                
                # Extract text
                extracted_text = extract_text_from_pdf_bytes(content_bytes)
                text_preview = extracted_text[:200] if extracted_text else "No text extracted"
                print(f"   📄 Content Preview: {text_preview}...")
                
                # Extract QR
                qr_content = extract_qr_from_pdf_bytes(content_bytes)
                print(f"   🔍 QR Content: {qr_content or 'No QR code found'}")
                
                # Store results
                results.append({
                    "Email Subject": subject,
                    "Sender": sender,
                    "Received Date": received_date,
                    "PDF Name": pdf_name,
                    "QR Content": qr_content,
                    "Text Preview": text_preview
                })

        # Create DataFrame
        df = pd.DataFrame(results)
        print("\n📊 Results DataFrame:")
        print(df)
        
        # Optionally save to CSV
        df.to_csv("pdf_analysis_results.csv", index=False)
        print("\n💾 Results saved to 'pdf_analysis_results.csv'")

    except Exception as e:
        print(f"❌ Test failed due to error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Test script starting...")
    test_email_pdf_fetch()
    print("Test script finished.")

