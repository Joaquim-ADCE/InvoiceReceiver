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
from utils.cleanup_utils import clean_pycache
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
      0. Clean up any stale __pycache__ folders
      1. Fetch today’s emails from SENDER_EMAIL with PDF attachments
      2. Extract and parse QR data from each PDF
      3. Validate vendors, remove duplicates (including header duplicates)
      4. For each new invoice:
         a. Post header to Navision
         b. Suggest GL account via GPT
         c. Build and post lines for each VAT category
      5. Send processing report
    """
    # ─── 0. Cache cleanup ──────────────────────────────────────────────────────
    clean_pycache()

    # ─── 1. Fetch and decode PDFs ─────────────────────────────────────────────
    print("📩 Fetching emails and PDFs...")
    client = GraphClient()
    email_items = fetch_emails_with_pdfs(client)

    records = []
    seen_attachments = set()

    for item in email_items:
        for att in item['pdf_attachments']:
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

    # ─── 2. Vendor validation & duplicate checks ───────────────────────────────
    valid_df, invalid_df = validate_vendors_by_nif(qr_df)
    new_df, dup_qr_df = check_if_invoices_are_registered(valid_df)

    print(f"✅ Invalid vendors: {len(invalid_df)}")
    print(f"✅ Duplicate invoices (QR): {len(dup_qr_df)}")
    print(f"📑 New invoices: {len(new_df)}")

    # ─── 3. Process each new invoice ──────────────────────────────────────────
    VAT_GROUP_MAP = {
        "I2": "OBS-ISEN", "I3": "OBS-RDZ", "K3": "OBSND-RDZA",
        "I5": "OBS-INT", "I7": "OBS-NOR", "J7": "OBS-NORMAD",
    }

    for idx, inv in new_df.iterrows():
        vendor_no     = inv['vendor_no']
        vendor_inv_no = inv['G']
        document_date = inv['F']
        pdf_content   = records[idx]['pdf_content']

        # 3a) Build & post header
        header_payload = build_header_payload(vendor_no, vendor_inv_no, document_date)
        resp_h = post_invoice_header(header_payload)
        if (not resp_h) or ('No' not in resp_h):
            log_invoice('', vendor_no, vendor_inv_no, 'FAILURE', 'HEADER post failed')
            continue
        document_no = resp_h['No']
        log_invoice(document_no, vendor_no, vendor_inv_no, 'SUCCESS', '')

        # 3b) Suggest GL via GPT
        gl_account = suggest_gl_account_from_pdf({'pdfs': [{'content': pdf_content}]}, vendor_no)

        # 3c) Post lines
        line_idx = 10000
        categories = [
            (['I2','J2','K2'], []),
            (['I3'], ['I4']), (['J3'], ['J4']), (['K3'], ['K4']),
            (['I5'], ['I6']), (['J5'], ['J6']), (['K5'], ['K6']),
            (['I7'], ['I8']), (['J7'], ['J8']), (['K7'], ['K8']),
        ]
        for base_keys, vat_keys in categories:
            base_amt = sum(float(str(inv.get(k) or "0").replace(",", ".")) for k in base_keys)
            vat_amt  = sum(float(str(inv.get(k) or "0").replace(",", ".")) for k in vat_keys)
            if not (base_amt or vat_amt):
                continue

            vat_group = next(
                (VAT_GROUP_MAP[k] for k in base_keys
                 if float(str(inv.get(k) or "0").replace(",", ".")) != 0),
                None
            )

            line_payload = build_line_payload(
                document_no, gl_account, base_amt, vat_amt,
                line_idx, vendor_no, vat_group
            )
            resp_l = post_invoice_line(line_payload)
            if resp_l and resp_l.get('Document_No') == document_no:
                log_invoice(document_no, vendor_no, vendor_inv_no, 'SUCCESS', '')
            else:
                log_invoice(document_no, vendor_no, vendor_inv_no, 'FAILURE', f'LINE{line_idx} post failed')
            line_idx += 10000

    # ─── 4. Send summary report ─────────────────────────────────────────────────
    send_report(period_days)


if __name__ == '__main__':
    orchestrate()
