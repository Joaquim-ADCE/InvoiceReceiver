import os
import requests
import base64
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_EMAIL = os.getenv("USER_EMAIL")
GRAPH_API_BASE = os.getenv("GRAPH_API_BASE_URL", "https://graph.microsoft.com/v1.0")
TOKEN_ENDPOINT = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPES = ["https://graph.microsoft.com/.default"]


class GraphClient:
    def __init__(self):
        self.access_token = self._get_access_token()

    def _get_access_token(self) -> str:
        payload = {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": " ".join(SCOPES),
        }
        response = requests.post(TOKEN_ENDPOINT, data=payload)
        response.raise_for_status()
        return response.json()["access_token"]

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def get_all_emails(self, top: int = 50) -> List[Dict]:
        """Fetch all emails (read and unread) with pagination and attachments."""
        headers = self._get_headers()
        messages = []
        url = f"{GRAPH_API_BASE}/users/{USER_EMAIL}/messages?$expand=attachments&$orderby=receivedDateTime desc&$top={top}"

        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            messages.extend(data.get("value", []))
            url = data.get("@odata.nextLink")

        return messages

    def get_all_emails_from(self, sender_email: str = "ngomes@adcecija.pt", top: int = 50) -> List[Dict]:
        """Fetch all emails and filter for those from a specific sender."""
        headers = self._get_headers()
        messages = []
        url = (
            f"{GRAPH_API_BASE}/users/{USER_EMAIL}/messages"
            f"?$expand=attachments"
            f"&$orderby=receivedDateTime desc"
            f"&$top={top}"
        )

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        all_messages = data.get("value", [])
        
        # Filter for emails from the specific sender
        messages = [
            msg for msg in all_messages
            if msg.get("from", {}).get("emailAddress", {}).get("address") == sender_email
        ]

        return messages

    def extract_attachments(self, message: Dict) -> List[Dict]:
        """Extract and decode attachments from a single email message."""
        attachments = []
        for att in message.get("attachments", []):
            if att.get("@odata.type") == "#microsoft.graph.fileAttachment":
                try:
                    decoded = base64.b64decode(att["contentBytes"])
                    attachments.append({
                        "name": att["name"],
                        "content": decoded,
                        "contentType": att["contentType"]
                    })
                except Exception as e:
                    print(f"Failed to decode {att['name']}: {e}")
        return attachments

    def save_attachments(self, message: Dict, save_dir: str = "attachments") -> None:
        """Save all attachments from a message to disk."""
        os.makedirs(save_dir, exist_ok=True)
        for attachment in self.extract_attachments(message):
            path = os.path.join(save_dir, attachment["name"])
            with open(path, "wb") as f:
                f.write(attachment["content"])
