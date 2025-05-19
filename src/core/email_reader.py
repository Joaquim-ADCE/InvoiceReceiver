from typing import List, Dict
from config.graph_api import GraphClient


def fetch_emails_with_pdfs(graph_client: GraphClient, top: int = 50) -> List[Dict]:
    """
    Fetch PDF attachments from today's emails sent by the configured sender.

    Args:
        graph_client: An authenticated GraphClient instance.
        top:         Maximum number of messages to retrieve.

    Returns:
        A list of dicts, each containing:
            - 'email': the Graph email object
            - 'pdf_attachments': a list of attachment dicts for PDFs
    """
    # Retrieve messages from today by sender (uses .env SENDER_EMAIL)
    messages = graph_client.get_emails_from_sender_today(top=top)

    results: List[Dict] = []
    for msg in messages:
        # Graph may require expanding attachments via query; ensure attachments key present
        attachments = msg.get('attachments', [])
        # Filter only PDF attachments
        pdfs = [att for att in attachments if att.get('contentType') == 'application/pdf']
        if pdfs:
            results.append({
                'email': msg,
                'pdf_attachments': pdfs
            })
    return results
