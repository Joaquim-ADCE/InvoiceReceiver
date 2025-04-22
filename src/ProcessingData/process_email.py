from ProcessingData.API.graph_api import get_access_token, send_email
from info.config import GRAPH_API_BASE_URL, MAILBOX_USER_ID
from qrcode import QRCode

import base64
import requests
import logging
import fitz
import cv2
import numpy as np


def fetch_email_details(email_id):
    """This function fetches the details of a specific email
    Args:
        email_id (str): The unique identifier of the email to fetch details for
        
    Returns:
        dict: A dictionary containing email details
    """
    access_token = get_access_token()
    if not access_token:
        logging.error("Unable to obtain access token")
        return None

    if "Messages/" in email_id:
        email_id = email_id.split("Messages/")[-1]
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = f"{GRAPH_API_BASE_URL}/users/{MAILBOX_USER_ID}/messages/{email_id}?$expand=attachments&$select=id,subject,sender,body,hasAttachments,receivedDateTime,internetMessageId"
    
    try:
        response = requests.get(url, headers=headers)
        logging.info(f"Getting email {email_id}: Status {str(response.status_code)}")
        
        # Check if the email was deleted or does not exist
        if response.status_code == 404:
            error_code = response.json().get('error', {}).get('code')
            if error_code == 'ErrorItemNotFound':
                logging.warning(f"Email {email_id} not found or deleted")
                return None
            
        if response.status_code == 200:
            email_data = response.json()
            
            # Process attachments
            attachments = []
            for attachment in email_data.get("attachments", []):
                try:
                    attachment_processed = {
                        "name": attachment.get("name", "Unknown"),
                        "contentType": attachment.get("contentType", "Unknown"),
                        "content": base64.b64decode(attachment.get("contentBytes", "")) if attachment.get("contentBytes") else None,
                        "size": attachment.get("size", 0)
                    }
                    attachments.append(attachment_processed)
                    logging.info(f"Processed attachment: {attachment_processed['name']}, Type: {attachment_processed['contentType']}, Size: {str(attachment_processed['size'])}")
                except Exception as e:
                    logging.error(f"Error processing attachment {attachment.get('name', 'Unknown')}: {str(e)}")
                    continue
            
            email_details = {
                "id": email_id,
                "internetMessageId": email_data.get("internetMessageId", ""),
                "sender": email_data["sender"]["emailAddress"],
                "subject": email_data["subject"],
                "body": email_data["body"]["content"],
                "attachments": attachments,
                "receivedDateTime": email_data.get("receivedDateTime", ""),
                "hasAttachments": bool(attachments)
            }
            
            logging.info(f"Email details: Subject: {email_details['subject']}, MessageID: {email_details['internetMessageId']}")
            logging.info(f"Number of attachments processed: {str(len(attachments))}")
            return email_details
        
        logging.error(f"Error fetching email. Status: {str(response.status_code)}")
        logging.error(f"Response: {response.text}")
        return None
            
    except Exception as e:
        logging.error(f"Error fetching email: {str(e)}")
        return None


def extract_attachments(email_id, email_data):
    """This function extracts the attachments from an email
    Args:
        email_id (str): The unique identifier of the email to extract attachments from
        email_data (dict): A dictionary containing email details
        
    Returns:
        list: A list of dictionaries containing attachment details
    """
    access_token = get_access_token()
    if not access_token:
        return []

    headers = {"Authorization": f"Bearer {access_token}"}
    attachments = []

    if "attachments" in email_data:
        for attachment in email_data["attachments"]:
            if "id" in attachment:
                attachment_id = attachment["id"]
                attachment_url = f"{GRAPH_API_BASE_URL}/users/{MAILBOX_USER_ID}/messages/{email_id}/attachments/{attachment_id}"
                response = requests.get(attachment_url, headers=headers)
                
                if response.status_code == 200:
                    attachment_data = response.json()
                    filename = attachment_data.get("name", "arquivo_desconhecido")
                    file_content = attachment_data.get("contentBytes")

                    if file_content:
                        file_data = base64.b64decode(file_content)
                        attachments.append({
                            "filename": filename,
                            "content": file_data,
                            "contentType": attachment_data.get("contentType", "application/octet-stream")
                        })

    return attachments


def extract_qr_code_from_email(attachments):
    """This function extracts the QR code from the first PDF found in the attachments
    Args:
        attachments (list): A list of dictionaries containing attachment details
        
    Returns:
        str: A string containing the QR code data
    """
    logging.info(f"Searching for QR code in {str(len(attachments))} attachments")
    
    for attachment in attachments:
        try:
            if not isinstance(attachment, dict):
                logging.error(f"Invalid attachment format: {str(type(attachment))}")
                continue

            logging.info(f"Processing attachment: {attachment.get('name', 'Unknown name')}")
            
            if attachment.get("contentType") != "application/pdf":
                logging.info(f"Skipping non-PDF attachment: {attachment.get('name', 'Unknown name')}")
                continue

            content = attachment.get("content")
            if not content:
                logging.error(f"No content found in attachment: {attachment.get('name', 'Unknown name')}")
                continue

            # Abre o PDF e processa cada página
            pdf_document = fitz.open(stream=content, filetype="pdf")
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Renderiza a página como uma imagem
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom para melhor qualidade
                img_data = pix.tobytes()
                
                # Converte para formato que o OpenCV pode ler
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is None:
                    logging.warning(f"Failed to convert page {page_num} to image")
                    continue
                
                # Converte para escala de cinza
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Aplica threshold adaptativo
                binary = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                )
                
                # Tenta diferentes métodos de detecção
                methods = [
                    lambda img: cv2.QRCodeDetector().detectAndDecode(img),
                    lambda img: cv2.QRCodeDetector().detectAndDecode(cv2.bitwise_not(img)),
                    lambda img: cv2.QRCodeDetector().detectAndDecode(binary)
                ]
                
                for method in methods:
                    try:
                        decoded_text, points, _ = method(gray)
                        
                        if decoded_text and decoded_text.count('*') >= 6:
                            logging.info(f"QR code found on page {page_num + 1}")
                            pdf_document.close()
                            return decoded_text
                            
                    except Exception as e:
                        logging.debug(f"QR detection method failed: {str(e)}")
                        continue
                
                # Tenta extrair e processar imagens individuais da página
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        nparr = np.frombuffer(image_bytes, np.uint8)
                        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        if image is None:
                            continue
                            
                        # Tenta diferentes processamentos na imagem
                        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                        binary = cv2.adaptiveThreshold(
                            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                        )
                        
                        for img_process in [gray, binary, cv2.bitwise_not(gray)]:
                            try:
                                decoded_text, points, _ = cv2.QRCodeDetector().detectAndDecode(img_process)
                                
                                if decoded_text and decoded_text.count('*') >= 6:
                                    logging.info(f"QR code found in image {img_index} on page {page_num + 1}")
                                    pdf_document.close()
                                    return decoded_text
                                    
                            except Exception as e:
                                logging.debug(f"QR detection failed for image {img_index}: {str(e)}")
                                continue
                                
                    except Exception as e:
                        logging.warning(f"Error processing image {img_index} on page {page_num}: {str(e)}")
                        continue
            
            pdf_document.close()

        except Exception as e:
            logging.error(f"Error processing attachment: {str(e)}")
            logging.error(f"Attachment details: {str(attachment)}")
            continue

    logging.warning("No QR code found in any attachment")
    return None


def get_info_from_qr_code(qr_code_matrix):
    """This function gets the information from the QR code
    Args:
        qr_code_matrix (str): A string containing the QR code data

    Returns:
        str: A string containing the QR code data
    """
    qr = QRCode()
    qr.add_data(qr_code_matrix)
    qr.make()

    return qr.get_matrix()


def extract_text_from_pdf(attachments):
    """This function extracts text from all PDFs in the attachments
    Args:
        attachments (list): A list of dictionaries containing attachment details

    Returns:
        list: A list of dictionaries containing text from each PDF
    """
    pdf_texts = []
    
    logging.info(f"Starting PDF text extraction from {len(attachments)} attachments")
    
    for attachment in attachments:
        try:
            if not isinstance(attachment, dict):
                logging.warning(f"Skipping invalid attachment format: {str(type(attachment))}")
                continue

            name = attachment.get("name", "Unknown")
            content_type = attachment.get("contentType", "Unknown")
            
            logging.info(f"Processing attachment: {name} (Type: {content_type})")

            if content_type != "application/pdf":
                logging.info(f"Skipping non-PDF attachment: {name}")
                continue

            content = attachment.get("content")
            
            if not content:
                logging.warning(f"No content found in PDF {name}")
                continue

            logging.info(f"Starting to process PDF: {name}")
            
            try:
                pdf_document = fitz.open(stream=content, filetype="pdf")
                
                if pdf_document.page_count == 0:
                    logging.warning(f"PDF {name} has no pages")
                    pdf_document.close()
                    continue

                text = ""
                processed_pages = 0
                
                for page_num in range(pdf_document.page_count):
                    try:
                        page = pdf_document[page_num]
                        page_text = page.get_text()
                        text += page_text
                        processed_pages += 1
                        text_length = len(page_text)
                        logging.info(f"Page {page_num + 1} of {name} processed: {text_length} characters")
                        if text_length > 0:
                            logging.info(f"Sample text from page {page_num + 1}: {page_text[:200]}...")
                        else:
                            logging.warning(f"No text found on page {page_num + 1}")
                            
                    except Exception as page_error:
                        logging.warning(f"Error processing page {page_num + 1} of {name}: {str(page_error)}")
                        continue
                
                if processed_pages > 0:
                    total_text_length = len(text)
                    if total_text_length > 0:
                        pdf_texts.append({
                            "filename": name,
                            "text": text,
                            "pages": str(processed_pages)
                        })
                        logging.info(f"PDF {name} processed successfully: {processed_pages} pages, {total_text_length} characters")
                    else:
                        logging.warning(f"No text content found in PDF {name} after processing {processed_pages} pages")
                else:
                    logging.warning(f"No pages could be processed in PDF {name}")
                
                pdf_document.close()
                
            except Exception as pdf_error:
                logging.error(f"Error processing PDF {name}: {str(pdf_error)}")
                continue
                
        except Exception as e:
            logging.error(f"Unexpected error processing attachment: {str(e)}")
            continue
    
    logging.info(f"Completed PDF text extraction. Processed {len(pdf_texts)} PDFs successfully")
    return pdf_texts


def orchestrate_email_processing(email_id):
    """This function orchestrates the email processing
    Args:
        email_id (str): The unique identifier of the email to process
        
    Returns:
        dict: A dictionary containing the email details
    """
    try:
        email_details = fetch_email_details(email_id)
        
        if email_details is None:
            logging.error(f"Unable to fetch details of email {email_id}")
            send_email(
                "Email não encontrado",
                f"Email não encontrado ou não pode ser processado.\nID do Email: {email_id}"
            )
            return None

        attachments = email_details.get("attachments", [])

        if not attachments:
            received_date = email_details['receivedDateTime'].split('T')[0]
            error_message = (
                f"Email não contém anexos\n\n"
                f"Para encontrar este email no Outlook:\n"
                f"1. Na caixa de pesquisa, digite: subject:'{email_details['subject']}' received:{received_date}\n"
                f"2. Ou pesquise por: {email_details['subject']}\n\n"
                f"Detalhes do Email:\n"
                f"Assunto: {email_details['subject']}\n"
                f"Data de Recebimento: {email_details['receivedDateTime']}\n"
                f"Remetente: {email_details['sender']['name'] if 'name' in email_details['sender'] else email_details['sender']['address']}"
            )
            logging.warning(f"Email {email_id} does not have attachments")
            send_email("Email sem anexos", error_message)
            return None

        qr_data = extract_qr_code_from_email(attachments)
        if not qr_data:
            received_date = email_details['receivedDateTime'].split('T')[0]
            error_message = (
                f"Não foi encontrado QR code nos anexos\n\n"
                f"Para encontrar este email no Outlook:\n"
                f"1. Na caixa de pesquisa, digite: subject:'{email_details['subject']}' received:{received_date}\n"
                f"2. Ou pesquise por: {email_details['subject']}\n\n"
                f"Detalhes do Email:\n"
                f"Assunto: {email_details['subject']}\n"
                f"Data de Recebimento: {email_details['receivedDateTime']}\n"
                f"Remetente: {email_details['sender']['name'] if 'name' in email_details['sender'] else email_details['sender']['address']}"
            )
            logging.warning(f"No QR code found in email {email_id}")
            send_email("QR Code não encontrado", error_message)
            return None

        pdf_text = extract_text_from_pdf(attachments)
        
        # Verifica se conseguiu extrair algum texto dos PDFs
        if not pdf_text:
            logging.warning(f"No text could be extracted from PDFs in email {email_id}")
            pdf_text = [{"filename": "No text", "text": "", "pages": "0"}]
        
        response = {
            "email_details": email_details,
            "pdf_texts": pdf_text,
            "qr_info": qr_data
        }
        logging.info(f"Email {email_id} processed: {str(len(pdf_text))} PDFs found")

        return response
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error processing email {email_id}: {error_msg}")
        send_email(
            "Erro no processamento",
            f"Ocorreu um erro ao processar o email.\nID do Email: {email_id}\nErro: {error_msg}"
        )
        return None
