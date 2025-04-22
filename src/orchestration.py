from ProcessingData.process_email import orchestrate_email_processing
from ProcessingData.DFprocess import process_df
from ProcessingData.DB.conection import fetch_from_table
from info.config import TABLES
from ProcessingData.transformations.process_transformations import process_invoice
from ProcessingData.API.graph_api import send_email


def orchestrate_all_processes(email_id):
    """This function orchestrates all the processes
    Steps:
        1. Process the email
        2. Process the dataframe
        3. Process the invoice
    Args:
        email_id (str): The ID of the email 
    """
    response = orchestrate_email_processing(email_id)
    if response is not None:
        df = process_df(response)
        if df is not None and df is not False:
            vendors_df = fetch_from_table(TABLES['vendors'], 'dbo')
            purchase_header_df = fetch_from_table(TABLES['purchase_header'], 'dbo')
            purchase_header_reg_df = fetch_from_table(TABLES['purchase_header_reg'], 'dbo')
            validation = process_invoice(df, vendors_df, purchase_header_df, purchase_header_reg_df)

            if validation == False:
                sender = response.get('email_details', {}).get('sender', {})
                sender_name = sender.get('name', sender.get('address', 'Unknown Sender'))

                send_email(
                    "Invalid invoice",
                    f"Invoice sent by {sender_name} already exists in Navision"
                )
                return False

            return True

    return False
