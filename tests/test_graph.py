# test_graph_api.py

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)

# Now we can import project modules
from config.graph_api import GraphClient
from dotenv import load_dotenv

def main():
    # Ensure .env is loaded if you're running this standalone
    load_dotenv()

    try:
        client = GraphClient()
    except Exception as e:
        print(f"❌ Failed to get a token or initialize GraphClient: {e}")
        sys.exit(1)

    try:
        emails = client.get_all_emails(top=10)
    except Exception as e:
        print(f"❌ Error fetching emails: {e}")
        sys.exit(1)

    if not emails:
        print("✅ No emails today")
    else:
        print(f"✅ Found {len(emails)} email(s) today:")
        for msg in emails:
            subj = msg.get("subject", "<no subject>")
            dt   = msg.get("receivedDateTime", "<no date>")
            print(f"  • {dt} — {subj}")

if __name__ == "__main__":
    main()
