from typing import List, Dict
from config.graph_api import GraphClient

def fetch_emails_with_pdfs(graph_client: GraphClient) -> List[Dict]:
    """
    Fetch emails in faturas@adcecija.pt mailbox that have at least one PDF attachment.

    Returns:
        A list of dicts, each with:
            - 'email': the email object
            - 'pdf_attachments': a list of attachment dicts that are PDFs
    """
    emails = graph_client.get_all_emails()
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

    return filtered
