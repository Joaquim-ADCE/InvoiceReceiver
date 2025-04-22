from flask import Flask, request, jsonify
import logging
from logging.handlers import RotatingFileHandler
import os
from info.config import WEBHOOK_PORT
from orchestration import orchestrate_all_processes
from datetime import datetime
import threading


app = Flask(__name__)
processed_emails = {}
processing_lock = threading.Lock()


def is_already_processed(email_id):
    """Check if the email has already been processed
    Args:
        email_id (str): The ID of the email to check
    Returns:
        bool: True if the email has already been processed, False otherwise
    """
    return email_id in processed_emails


def process_email_background(email_id, event):
    """This function orchestrates all processes for an email
    Args:
        email_id (str): The ID of the email to process
        event (dict): The event data
    """
    try:
        result = orchestrate_all_processes(email_id)
        
        if isinstance(result, dict) and result.get('not_found'):
            logging.info(f"Email {email_id} not found - removing from control")
            return
            
        if result:
            logging.info(f"Email {email_id} processed successfully")
        else:
            logging.warning(f"Email {email_id} could not be processed")
    except Exception as e:
        logging.error(f"Error processing email {email_id}: {str(e)}")
    finally:
        with processing_lock:
            pass


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """This function handles the webhook"""
    validation_token = request.args.get("validationToken")
    if validation_token:
        logging.info(f"Validation token received: {validation_token}")
        return validation_token, 200, {'Content-Type': 'text/plain'}

    if request.method == "POST":
        try:
            if not request.is_json:
                return jsonify({"status": "error"}), 415

            response = jsonify({"status": "success"}), 200
            
            data = request.get_json()
            if "value" in data:
                for event in data["value"]:
                    email_id = event.get("resource", "").split('/')[-1]

                    with processing_lock:
                        if not is_already_processed(email_id):
                            processed_emails[email_id] = {
                                'timestamp': datetime.now(),
                                'event': event
                            }
                            thread = threading.Thread(
                                target=process_email_background,
                                args=(email_id, event),
                                daemon=True
                            )
                            thread.start()
                            logging.info(f"Thread started for email {email_id}")
                        else:
                            logging.info(f"Email {email_id} is already being processed")

            return response

        except Exception as e:
            logging.error(f"Erro no webhook: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 200

    return jsonify({"status": "error", "message": "Method not allowed"}), 405


def setup_logging():
    """Configura o sistema de logging"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    file_handler = RotatingFileHandler("logs/app.log", maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def start_webhook():
    """Inicia o servidor webhook"""
    try:
        logging.info("Starting webhook server...")
        app.run(host='0.0.0.0', port=WEBHOOK_PORT, debug=False, use_reloader=False)
    except Exception as e:
        logging.error(f"Error starting webhook: {str(e)}")


if __name__ == "__main__":
    setup_logging()
    start_webhook()
