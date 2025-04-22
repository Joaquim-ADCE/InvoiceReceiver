import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Microsoft Azure AD credentials
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Webhook configuration
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 5048))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Microsoft Graph API configuration
GRAPH_API_BASE_URL = os.getenv("GRAPH_API_BASE_URL", "https://graph.microsoft.com/v1.0")
SUBSCRIPTION_URL = f"{GRAPH_API_BASE_URL}/subscriptions"
MAILBOX_USER_ID = os.getenv("MAILBOX_USER_ID")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHATGPT_MODEL = os.getenv("CHATGPT_MODEL", "gpt-4")

# Logging configuration
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

# Application settings
DEBUG_MODE = os.getenv("DEBUG_MODE", "True").lower() in ("true", "1", "t", "yes")

# Email configuration
DESTINATION_EMAIL = os.getenv("DESTINATION_EMAIL")
# If DESTINATION_EMAIL contains commas, convert it to a list
if DESTINATION_EMAIL and "," in DESTINATION_EMAIL:
    DESTINATION_EMAIL = [email.strip() for email in DESTINATION_EMAIL.split(",")]

# Database tables
TABLES = {
    'vendors': '[ADC$Vendor]',
    'purchase_header': '[ADC$Purchase Header]',
    'purchase_line': '[ADC$Purchase Line]',
    'purchase_header_reg': '[ADC$Purch_ Inv_ Header]'
}

def check_config():
    """Check if all required configuration variables are set."""
    missing_vars = [var for var in ["TENANT_ID", "CLIENT_ID", "CLIENT_SECRET", "OPENAI_API_KEY"] 
                   if not globals().get(var)]
    if missing_vars:
        print(f"⚠️ AVISO: As seguintes variáveis de configuração não foram definidas: {', '.join(missing_vars)}")
        print("🔹 Certifique-se de definir essas variáveis no arquivo .env.")

check_config()
