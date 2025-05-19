#!/usr/bin/env python3
"""
Orchestrator script: fetch emails, extract QR data, validate and dedupe invoices,
post headers and lines to Navision, log results, and send a report email.
"""
import os
import sys
import base64
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Setup repo root and load env
repo_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(repo_root))
load_dotenv()

# Imports
from config.graph_api import GraphClient
from src.core.email_reader import fetch_emails_with_pdfs
from src.core.qr_reader import extract_qr_from_pdf_bytes
from utils.qr_utils import parse_qr_to_dataframe
from src.core.vendor_validation import validate_vendors_by_nif
from src.core.invoice_validation import check_if_invoices_are_registered
from src.core.header_payload import build_header_payload
from src.core.line_payload import build_line_payload
from config.navision_api import post_invoice_header, post_invoice_line
from utils.invoice_logger import log_invoice
from utils.report_generator import send_report
from src.core.openai_client import suggest_gl_account_from_pdf

def orchestrate(period_days: int = 1):
    """
    Full pipeline for invoice insertion:
      1. Fetch today’s emails from SENDER_EMAIL with PDF attachments
      2. Extract and parse QR data from each PDF
      3. Validate vendors, remove duplicates
      4. For each new invoice:
         a. Post header to Navision
         b. Suggest GL account via GPT
         c. Build and post lines for each VAT category (with VAT_Prod_Posting_Group)
      5. Send processing report
    """
    print("📩 Fetching emails and PDFs...")
    client = GraphClient()
    email_items = fetch_emails_with_pdfs(client)

    records = []
    seen_attachments = set()

    for item in email_items:
        for att in item['pdf_attachments']:
            # Deduplicate by attachment id or name
            att_key = att.get('id') or att.get('name')
            if att_key in seen_attachments:
                continue
            seen_attachments.add(att_key)

            pdf_name = att.get('name', 'unnamed.pdf')
            try:
                content = base64.b64decode(att['contentBytes'])
            except Exception as e:
                log_invoice('', '', pdf_name, 'FAILURE', f'Decode error: {e}')
                continue

            qr_str = extract_qr_from_pdf_bytes(content)
            if not qr_str:
                log_invoice('', '', pdf_name, 'FAILURE', 'No QR code found')
                continue

            df = parse_qr_to_dataframe(qr_str)
            if df.empty:
                log_invoice('', '', pdf_name, 'FAILURE', 'QR parse returned empty')
                continue

            row = df.iloc[0].to_dict()
            row['pdf_name'] = pdf_name
            row['pdf_content'] = content
            records.append(row)

    if not records:
        print("❌ No valid QR data to process.")
        return

    qr_df = pd.DataFrame(records)
    # Vendor validation
    valid_df, invalid_df = validate_vendors_by_nif(qr_df)
    # Duplicate check
    new_df, dup_df = check_if_invoices_are_registered(valid_df)

    print(f"✅ Invalid vendors: {len(invalid_df)}")
    print(f"✅ Duplicate invoices: {len(dup_df)}")
    print(f"📑 New invoices: {len(new_df)}")

    # Mapping from QR fields to Navision VAT Prod Posting Group
    VAT_GROUP_MAP = {
        "I2": "OBS-ISEN",
        "I3": "OBS-RDZ",
        "K3": "OBSND-RDZA",
        "I5": "OBS-INT",
        "I7": "OBS-NOR",
        "J7": "OBS-NORMAD",
    }

    # Process each new invoice
    for idx, inv in new_df.iterrows():
        vendor_no     = inv['vendor_no']
        vendor_inv_no = inv['G']
        document_date = inv['F']
        pdf_content   = records[idx]['pdf_content']

        # 1) Build and post header
        header_payload = build_header_payload(vendor_no, vendor_inv_no, document_date)
        resp_h = post_invoice_header(header_payload)
        if not resp_h or 'No' not in resp_h:
            log_invoice('', vendor_no, vendor_inv_no, 'FAILURE', 'HEADER post failed')
            continue
        document_no = resp_h['No']
        log_invoice(document_no, vendor_no, vendor_inv_no, 'SUCCESS', '')

        # 2) Suggest GL account via GPT
        gl_account = suggest_gl_account_from_pdf({'pdfs': [{'content': pdf_content}]}, vendor_no)

        # 3) Build and post lines for each VAT category
        categories = [
            (['I2','J2','K2'], []),  # 0% VAT
            (['I3'], ['I4']),        # 6% VAT
            (['J3'], ['J4']),        # 5% VAT
            (['K3'], ['K4']),        # 4% VAT
            (['I5'], ['I6']),        # 13% VAT
            (['J5'], ['J6']),        # 12% VAT
            (['K5'], ['K6']),        # 9% VAT
            (['I7'], ['I8']),        # 23% VAT
            (['J7'], ['J8']),        # 22% VAT
            (['K7'], ['K8']),        # 16% VAT
        ]
        line_idx = 1

        for base_keys, vat_keys in categories:
            # Sum up base and VAT amounts
            base_amt = sum(float(inv.get(k) or 0) for k in base_keys)
            vat_amt  = sum(float(inv.get(k) or 0) for k in vat_keys)

            if base_amt or vat_amt:
                # Pick VAT Prod Posting Group based on first non-zero base key
                vat_group = None
                for key in base_keys:
                    try:
                        if float(inv.get(key) or 0) != 0:
                            vat_group = VAT_GROUP_MAP.get(key)
                            break
                    except ValueError:
                        continue

                line_payload = build_line_payload(
                    document_no=document_no,
                    account_no=gl_account,
                    amount_excl=base_amt,
                    vat_amount=vat_amt,
                    line_index=line_idx,
                    vendor_no=vendor_no,
                    vat_prod_posting_group=vat_group
                )
                resp_l = post_invoice_line(line_payload)
                if resp_l and resp_l.get('Document_No') == document_no:
                    log_invoice(document_no, vendor_no, vendor_inv_no, 'SUCCESS', '')
                else:
                    log_invoice(document_no, vendor_no, vendor_inv_no, 'FAILURE', f'LINE{line_idx} post failed')
                line_idx += 1

    # 4) Send summary report
    send_report(period_days)


if __name__ == '__main__':
    orchestrate()
