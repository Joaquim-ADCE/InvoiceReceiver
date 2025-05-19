# === openai_client_2.py (parametrized model for larger context windows) ===
import logging
import os
import re
import pandas as pd
from difflib import get_close_matches
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
from config.navision_api import get_vendor_history, get_gl_accounts
from src.core.pdf_reader import extract_text_from_pdf_bytes
from legacy.debug_gpt_inputs import debug_save_df, debug_log_gpt_input

# Allow switching model via env; default to 32k context
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4-turbo-32k")
client = OpenAI(api_key=os.getenv("GPT_KEY"))

def find_gl_by_text_similarity(vendor_history, pdf_text):
    descriptions = vendor_history['Description'].dropna().astype(str).tolist()
    if not descriptions:
        return None
    vectorizer = CountVectorizer().fit(descriptions + [pdf_text])
    vectors = vectorizer.transform(descriptions + [pdf_text])
    sims = cosine_similarity(vectors[-1], vectors[:-1]).flatten()
    vh = vendor_history.copy()
    vh['similarity'] = sims
    top = vh.sort_values('similarity', ascending=False).head(5)
    return top['No_line'].value_counts().idxmax()

def find_gl_by_amount(vendor_history, target_amount):
    if "Amount" not in vendor_history.columns:
        return None
    vh = vendor_history.copy()
    vh['diff'] = (vh['Amount'] - target_amount).abs()
    closest = vh.sort_values('diff').head(3)
    return closest['No_line'].value_counts().idxmax()

def extract_amount_from_text(text):
    amounts = re.findall(r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})\b", text)
    if not amounts:
        return None
    try:
        vals = [float(a.replace('.', '').replace(',', '.')) for a in amounts]
        return max(vals)
    except:
        return None

def suggest_gl_account_from_pdf(email_details, vendor_no):
    logging.info("🧠 Classifying invoice for GL account suggestions...")
    try:
        gl_full = get_gl_accounts()
        required = {'No','Name','Account_Category'}
        if not required.issubset(gl_full.columns):
            missing = required - set(gl_full.columns)
            raise KeyError(f"Missing columns: {missing}")

        # Pre-filter GLs starting with 6
        gl_full = gl_full[gl_full['No'].astype(str).str.startswith('6')]
        full_history = get_vendor_history()
        vendor_history = full_history[full_history['Buy_from_Vendor_No']==vendor_no]
        if vendor_history.empty or 'No_line' not in vendor_history.columns:
            logging.warning(f"No history for vendor {vendor_no}")
            return "❗️ No vendor history. Manual classification required."

        # Candidates: history GLs + same category
        hist = vendor_history['No_line'].astype(str).unique().tolist()
        gl_hist = gl_full[gl_full['No'].isin(hist)]
        cats = set(gl_hist['Account_Category'])
        gl_cat = gl_full[gl_full['Account_Category'].isin(cats)]
        gl_cand = pd.concat([gl_hist, gl_cat]).drop_duplicates('No')
        gl_df = gl_cand[['No','Name']].rename(columns={'No':'No_','Name':'Description'})
        valid = gl_df['No_'].tolist()
        debug_save_df(gl_df, 'gl_accounts_filtered')

        # Dominant historical GL
        cnt = vendor_history['No_line'].value_counts()
        top_gl = cnt.idxmax()
        if cnt.max()/cnt.sum()*100 >= 80:
            return top_gl

        # Invoice snippet
        text_all = ''
        for p in email_details.get('pdfs',[]):
            t = extract_text_from_pdf_bytes(p.get('content',b''))
            if t: text_all += '\n'+t
        lines = text_all.splitlines()
        snippet = '\n'.join(lines[:15])[:800]

        # Build filtered prompt
        gl_list = '\n'.join(f"{r.No_}: {r.Description}" for _,r in gl_df.iterrows())
        ex = '\n'.join(f"- '{r.Description[:60]}' → {r.No_line}" for _,r in vendor_history.head(3).iterrows())
        prompt = (
            "You are a Portuguese accounting assistant.\n"
            f"Vendor: {vendor_no}\n"
            f"History samples:\n{ex}\n\n"
            f"Invoice snippet:\n{snippet}\n\n"
            f"Candidate GL accounts:\n{gl_list}\n\n"
            "Respond ONLY with the 6-digit GL account number."
        )
        debug_log_gpt_input(vendor_no, prompt)

        # GPT call with larger context model
        for i in range(3):
            try:
                resp = client.chat.completions.create(
                    model=GPT_MODEL,
                    messages=[
                        {'role':'system','content':'Return only a 6-digit GL account number.'},
                        {'role':'user','content':prompt}
                    ],
                    temperature=0,
                    max_tokens=10
                )
                ans = resp.choices[0].message.content.strip()
                m = re.search(r"\b6\d{5}\b", ans)
                if m and m.group(0) in valid:
                    return m.group(0)
            except Exception as e:
                logging.error(f"GPT call {i+1} failed: {e}")

        # Fallbacks
        amt = extract_amount_from_text(text_all)
        by_text = find_gl_by_text_similarity(vendor_history, text_all)
        by_amt = find_gl_by_amount(vendor_history, amt) if amt else None
        for cand in (by_text, by_amt, top_gl):
            if cand in valid:
                return cand
        return "❗️ Manual classification required"

    except Exception as ex:
        logging.error(f"Classification pipeline failed: {ex}")
        return "❗️ Classification error"

# === End of openai_client_2.py ===
