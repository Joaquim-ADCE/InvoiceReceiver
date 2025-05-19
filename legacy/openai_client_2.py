# === Revised openai_client_2.py ===

import logging
import openai
import pandas as pd
import os
import re
from difflib import get_close_matches
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config.navision_api import get_vendor_history, get_gl_accounts
from src.core.pdf_reader import extract_text_from_pdf_bytes
from legacy.debug_gpt_inputs import debug_save_df, debug_log_gpt_input

openai.api_key = os.getenv("GPT_KEY")

def find_gl_by_text_similarity(vendor_history, pdf_text):
    descriptions = vendor_history['Description'].dropna().astype(str).tolist()
    if not descriptions:
        return None

    vectorizer = CountVectorizer().fit(descriptions + [pdf_text])
    vectors = vectorizer.transform(descriptions + [pdf_text])
    sims = cosine_similarity(vectors[-1], vectors[:-1]).flatten()

    vendor_history = vendor_history.copy()
    vendor_history['similarity'] = sims
    top_matches = vendor_history.sort_values('similarity', ascending=False).head(5)
    return top_matches['No_line'].value_counts().idxmax()

def find_gl_by_amount(vendor_history, target_amount):
    if "Amount" not in vendor_history.columns:
        return None
    vendor_history = vendor_history.copy()
    vendor_history['diff'] = (vendor_history['Amount'] - target_amount).abs()
    closest = vendor_history.sort_values('diff').head(3)
    return closest['No_line'].value_counts().idxmax()

def extract_amount_from_text(text):
    amounts = re.findall(r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})\b", text)
    if not amounts:
        return None
    try:
        values = [float(a.replace('.', '').replace(',', '.')) for a in amounts]
        return max(values)
    except:
        return None

def suggest_gl_account_from_pdf(email_details, vendor_no):
    logging.info("🧠 Asking GPT for GL account suggestions (history + GPT)...")

    try:
        gl_df = get_gl_accounts()
        logging.info(f"🔍 Columns in GL accounts: {gl_df.columns.tolist()}")

        if 'No' not in gl_df.columns:
            logging.error(f"❌ Missing 'No' in GL accounts: found columns {gl_df.columns.tolist()}")
            raise KeyError("'No' column is missing from GL accounts.")

        gl_df = gl_df[gl_df['No'].astype(str).str.startswith("6")][['No']]
        gl_df = gl_df.rename(columns={"No": "No_"})
        valid_accounts = gl_df['No_'].tolist()
        debug_save_df(gl_df, "gl_accounts_filtered")

        full_history = get_vendor_history()
        vendor_history = full_history[full_history['Buy_from_Vendor_No'] == vendor_no]

        if vendor_history.empty or 'No_line' not in vendor_history.columns:
            logging.warning(f"🚫 No usable invoice history found for vendor {vendor_no}")
            return "❗️ No vendor history found. Manual classification required."

        debug_save_df(vendor_history, f"vendor_history_{vendor_no}")

        gl_counts = vendor_history['No_line'].value_counts()
        top_gl = gl_counts.idxmax()
        top_pct = (gl_counts.max() / gl_counts.sum()) * 100

        if top_pct >= 80:
            logging.info(f"✅ History suggests GL {top_gl} with {top_pct:.2f}% confidence.")
            return top_gl

        combined_text = ""
        for p in email_details.get("pdfs", []):
            text = extract_text_from_pdf_bytes(p.get("content", b""))
            if text:
                combined_text += "\n" + text

        invoice_lines = combined_text.splitlines()
        invoice_snippet = "\n".join(invoice_lines[:15])[:1000] if invoice_lines else ""

        history_examples = vendor_history[['Description', 'No_line']].dropna().head(5)
        examples = "\n".join(f"- \"{row.Description[:80]}\" → {row.No_line}" for _, row in history_examples.iterrows())

        prompt = (
            "You are a Portuguese accounting assistant helping classify expense invoices into GL accounts.\n\n"
            f"Vendor No: {vendor_no}\n"
            f"Vendor History Examples:\n{examples}\n\n"
            f"Invoice Text:\n{invoice_snippet}\n\n"
            "Respond ONLY with the 6-digit GL account number (starts with 6)."
        )

        debug_log_gpt_input(vendor_no, prompt)

        for attempt in range(1, 4):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Respond ONLY with a 6-digit GL account number starting with 6."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    max_tokens=20
                )
                raw = response.choices[0].message["content"].strip()
                logging.info(f"🧠 GPT raw output: {raw}")
                match = re.search(r"\b6\d{5}\b", raw)
                if match:
                    gl_candidate = match.group(0)
                    if gl_candidate in valid_accounts:
                        return gl_candidate
                    else:
                        close = get_close_matches(gl_candidate, valid_accounts, n=1, cutoff=0.6)
                        if close:
                            return close[0]
            except Exception as e:
                logging.error(f"GPT call failed (attempt {attempt}): {e}")

        logging.warning("❌ GPT failed. Trying fallback logic...")

        amount = extract_amount_from_text(combined_text)
        gl_by_text = find_gl_by_text_similarity(vendor_history, combined_text)
        gl_by_amount = find_gl_by_amount(vendor_history, amount) if amount else None

        for gl in [gl_by_text, gl_by_amount, top_gl]:
            if gl in valid_accounts:
                logging.info(f"✅ Fallback returned GL: {gl}")
                return gl

        return "❗️ No valid GL could be inferred. Manual classification required."

    except Exception as e:
        logging.error(f"❌ Full classification process failed: {e}")
        return "❗️ Classification failed. Manual intervention required."


# === End of openai_client_2.py ===
