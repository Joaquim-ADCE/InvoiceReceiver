from Hook.webhook import app, start_webhook, setup_logging
import logging
from ProcessingData.process_email import fetch_email_details
from ProcessingData.API.chatgpt import send_message
from ProcessingData.API.graph_api import subscribe_to_emails
import threading
import time


if __name__ == "__main__":
    setup_logging()
    
    try:
        webhook_thread = threading.Thread(target=start_webhook)
        webhook_thread.daemon = True
        webhook_thread.start()
        
        logging.info("Waiting for webhook to start...")
        time.sleep(2)
        
        logging.info("Registering webhook in Microsoft Graph...")
        subscribe_to_emails()
        
        logging.info("System started and waiting for emails...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logging.info("\nStopping system...")
    except Exception as e:
        logging.error(f"Error starting system: {str(e)}")
