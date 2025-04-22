import requests
import logging
from info.config import OPENAI_API_KEY


def send_message(email_details, account_vendor):
    """This function sends a message to the ChatGPT API
    Steps:
        1. Send the message to the ChatGPT API
        2. Validate the response is a valid account number
        3. Return the validated account number
    Args:
        email_details (dict): The details of the email
        account_vendor (pd.DataFrame): The account vendor data
    Returns:
        str: The validated account number from the ChatGPT API
    """
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    # Log dos PDFs recebidos
    pdf_texts = email_details.get('pdf_texts', [])
    logging.info(f"Number of PDFs received: {len(pdf_texts)}")
    for i, pdf in enumerate(pdf_texts):
        logging.info(f"PDF {i+1}:")
        logging.info(f"  Filename: {pdf.get('filename', 'No filename')}")
        logging.info(f"  Content length: {len(pdf.get('text', ''))}")
        logging.info(f"  First 200 chars: {pdf.get('text', '')[:200]}")

    anexos = [f"Arquivo: {pdf['filename']}, Conteúdo: {pdf['text']}" 
              for pdf in pdf_texts]
    anexos_str = "\n".join(anexos)

    # Log do conteúdo que será enviado
    logging.info(f"Sending to ChatGPT - Attachments content length: {len(anexos_str)}")

    # Extrai apenas os números das contas disponíveis para validação posterior
    valid_accounts = account_vendor['No_'].tolist()
    logging.info(f"Available accounts: {valid_accounts}")
    
    prompt = (
        "Você é um assistente especializado em análise de documentos e correspondência contábil.\n\n"
        "### 📊 Contas Disponíveis:\n"
        f"{account_vendor.to_string()}\n\n"
        "### 📧 Email:\n"
        f"- Remetente: {email_details.get('sender', '')}\n"
        f"- Assunto: {email_details.get('subject', '')}\n"
        f"- Conteúdo: {email_details.get('body', '')}\n"
        f"- Anexos: {anexos_str}\n\n"
        "📌 IMPORTANTE: Retorne APENAS o número exato da conta (No_) que melhor corresponde. "
        "A resposta deve ser EXATAMENTE igual a um dos números de conta listados acima, sem texto adicional."
    )

    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "Você é um assistente especializado em classificação contábil. Responda APENAS com o número da conta, sem texto adicional."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 10  # Reduzido para garantir apenas o número da conta
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            account_number = response.json()["choices"][0]["message"]["content"].strip()
            logging.info(f"ChatGPT response: '{account_number}'")
            
            # Valida se a resposta é uma conta válida
            if account_number not in valid_accounts:
                logging.error(f"ChatGPT returned invalid account number: '{account_number}'")
                logging.error(f"Valid accounts are: {valid_accounts}")
                return False
            
            logging.info(f"Valid account number found: {account_number}")
            return account_number
        else:
            logging.error(f"Error in ChatGPT API: {response.status_code}")
            logging.error(f"Response content: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Exception in ChatGPT API: {str(e)}")
        return False
