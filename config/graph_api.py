import os
import requests
import base64
from typing import List, Dict
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

load_dotenv()

TENANT_ID        = os.getenv("TENANT_ID")
CLIENT_ID        = os.getenv("CLIENT_ID")
CLIENT_SECRET    = os.getenv("CLIENT_SECRET")
USER_EMAIL       = os.getenv("USER_EMAIL")
SENDER_EMAIL     = os.getenv("SENDER_EMAIL")
GRAPH_API_BASE   = os.getenv("GRAPH_API_BASE_URL", "https://graph.microsoft.com/v1.0")
TOKEN_ENDPOINT   = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPES           = ["https://graph.microsoft.com/.default"]

class GraphClient:
    def __init__(self):
        self.access_token = self._get_access_token()

    def _get_access_token(self) -> str:
        payload = {
            "grant_type":    "client_credentials",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope":         " ".join(SCOPES),
        }
        r = requests.post(TOKEN_ENDPOINT, data=payload)
        r.raise_for_status()
        return r.json()["access_token"]

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def get_emails_from_sender_today(self, top: int = 50) -> List[Dict]:
        """
        Fetch up to `top` messages sent by SENDER_EMAIL, received since
        00:00 in Europe/Lisbon local time today, newest first.
        """
        # 1) Load sender and compute midnight today in Lisbon
        sender = SENDER_EMAIL
        tz = ZoneInfo("Europe/Lisbon")
        today_midnight = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        # 2) Convert to UTC ISO format for Graph
        since_utc = today_midnight.astimezone(ZoneInfo("UTC")).isoformat()

        # 3) Build the OData filter
        filter_query = (
            f"receivedDateTime ge {since_utc} "
            f"and from/emailAddress/address eq '{sender}'"
        )

        # 4) Use params to let requests handle URL-encoding
        params = {
            "$filter":  filter_query,
            "$expand":  "attachments",
            "$orderby": "receivedDateTime desc",
            "$top":     str(top),
        }
        url = f"{GRAPH_API_BASE}/users/{USER_EMAIL}/messages"

        r = requests.get(url, headers=self._get_headers(), params=params)
        r.raise_for_status()
        return r.json().get("value", [])

    def get_all_emails(self, top: int = 50) -> List[Dict]:
        """
        Alias for get_emails_from_sender_today to avoid changing call sites.
        """
        return self.get_emails_from_sender_today(top)
