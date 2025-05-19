# config/graph_api.py
import os
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

class GraphClient:
    BASE_URL = 'https://graph.microsoft.com/v1.0'
    SENDER_EMAIL = os.getenv('PDF_SENDER_EMAIL')
    USER_EMAIL = os.getenv('USER_EMAIL')
    TOKEN_URL = f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}/oauth2/v2.0/token"

    def __init__(self):
        self._token = None

    def _get_token(self):
        # existing token retrieval logic...
        return self._token

    def _get_headers(self):
        token = self._get_token()
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    def get_emails_from_sender_today(self, top: int = 50):
        """
        Retrieves all messages sent by SENDER_EMAIL received since local midnight, following pagination.
        """
        # Calculate ISO dates for today in UTC
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        filter_query = (
            f"from/emailAddress/address eq '{self.SENDER_EMAIL}' and "
            f"receivedDateTime ge {start_of_day.isoformat()}"
        )
        url = f"{self.BASE_URL}/users/{self.USER_EMAIL}/mailFolders/Inbox/messages"
        params = {
            '$filter': filter_query,
            '$orderby': 'receivedDateTime desc',
            '$top': top,
            '$expand': 'attachments'
        }
        headers = self._get_headers()

        messages = []
        while url:
            resp = requests.get(url, headers=headers, params=params if messages == [] else None)
            resp.raise_for_status()
            data = resp.json()
            messages.extend(data.get('value', []))
            # Prepare nextLink for pagination, then clear params
            url = data.get('@odata.nextLink')
            params = None

        return messages

# Other methods...
