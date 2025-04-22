import requests
from info.config import (
    TENANT_ID, 
    CLIENT_ID, 
    CLIENT_SECRET, 
    GRAPH_API_BASE_URL,
    WEBHOOK_URL,
    MAILBOX_USER_ID,
    DESTINATION_EMAIL
)
from datetime import datetime, timedelta
import logging


_token_cache = {
    "access_token": None,
    "expires_at": None
}


def get_access_token():
    """This function gets an access token from the Azure AD, using cache when possible"""
    global _token_cache
    
    now = datetime.utcnow()
    if (_token_cache["access_token"] and _token_cache["expires_at"] 
        and now < _token_cache["expires_at"]):
        logging.info("Using cached token")
        return _token_cache["access_token"]

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }

    logging.info("Requesting new access token...")

    try:
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)

            if access_token:
                _token_cache["access_token"] = access_token
                _token_cache["expires_at"] = now + timedelta(seconds=expires_in - 300)
                logging.info("Token obtained and cached successfully")
                return access_token

        logging.error(f"Error getting token. Status: {response.status_code}")
        return None

    except Exception as e:
        logging.error(f"Exception getting token: {str(e)}")
        return None


def subscribe_to_emails():
    """This function subscribes to new emails with specific filters"""
    access_token = get_access_token()
    if not access_token:
        logging.error("Unable to obtain access token")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    start_time = datetime.utcnow().date().isoformat()
    expiration_date = (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

    filters = [
        f"receivedDateTime ge {start_time}",
        "hasAttachments eq true",
        "isDraft eq false"
    ]

    resource = (
        f"users/{MAILBOX_USER_ID}/messages"
        f"?$filter={' and '.join(filters)}"
    )

    payload = {
        "changeType": "created",
        "notificationUrl": WEBHOOK_URL,
        "resource": resource,
        "expirationDateTime": expiration_date,
        "clientState": "EmailMonitoringApp"
    }

    logging.info("Iniciando subscrição com filtros:")
    logging.info(f"- Data inicial: {start_time}")
    logging.info(f"- Resource URL: {resource}")

    try:
        response = requests.post(
            f"{GRAPH_API_BASE_URL}/subscriptions",
            headers=headers,
            json=payload
        )

        logging.info(f"Response status: {response.status_code}")
        logging.info(f"Response body: {response.text}")

        if response.status_code == 201:
            subscription_data = response.json()
            logging.info(f"Webhook subscribed successfully. ID: {subscription_data.get('id')}")
            return True
        else:
            logging.error(f"Error subscribing webhook: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return False

    except Exception as e:
        logging.error(f"Exception in subscription: {str(e)}")
        return False


def send_email(subject, message):
    """This function sends an email using the Microsoft Graph API
    Steps:
        1. Get the access token
        2. Send the email
    Args:
        subject (str): The subject of the email
        message (str): The message of the email
    """
    access_token = get_access_token()
    if not access_token:
        logging.error("Unable to obtain access token")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Garante que DESTINATION_EMAIL seja sempre uma lista
    if isinstance(DESTINATION_EMAIL, str):
        email_list = [DESTINATION_EMAIL]
    elif isinstance(DESTINATION_EMAIL, list):
        email_list = DESTINATION_EMAIL
    else:
        logging.error(f"Invalid DESTINATION_EMAIL format: {type(DESTINATION_EMAIL)}")
        return False

    # Verifica se há pelo menos um email válido
    if not email_list:
        logging.error("No valid destination emails")
        return False

    primary_recipient = email_list[0]
    cc_recipients = email_list[1:] if len(email_list) > 1 else []

    email_data = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": message
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": primary_recipient
                    }
                }
            ]
        }
    }

    # Adiciona CC apenas se houver destinatários em cópia
    if cc_recipients:
        email_data["message"]["ccRecipients"] = [
            {
                "emailAddress": {
                    "address": email
                }
            } for email in cc_recipients
        ]

    url = f"{GRAPH_API_BASE_URL}/users/{MAILBOX_USER_ID}/sendMail"
    
    try:
        response = requests.post(url, headers=headers, json=email_data)
        if response.status_code == 202:
            logging.info("Email sent successfully")
            return True
        else:
            logging.error(f"Error sending email: {response.status_code}")
            logging.error(f"Details: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Exception sending email: {str(e)}")
        return False
