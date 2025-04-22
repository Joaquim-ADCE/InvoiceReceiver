import pandas as pd
from ProcessingData.DB.conection import fetch_from_table, fetch_account_vendor
from ProcessingData.API.chatgpt import send_message
from info.config import TABLES
from ProcessingData.API.graph_api import send_email
import logging


def initial_validation(df, response):
    """This function validates the initial invoice data
    Args:
        df (pd.DataFrame): The dataframe containing the invoice data
        response (dict): The response from the email processing
        
    Returns:
        pd.DataFrame: The dataframe containing the validated invoice data
        or 
        bool: False if the invoice is not valid
    """
    vendors_df = fetch_from_table(TABLES['vendors'], 'dbo')
    
    if df.iloc[0]['B'] != '513631984':
        send_email(
                "Invoice wrong issued",
                f"Invoice sent by {response.get('email_details').get('sender').get('emailAddress').get('name')} it is not valid because it does not match the expected NIF number"
            )
        return False

    vendor_name = vendors_df.loc[vendors_df["VAT Registration No_"] == df.iloc[0]['A'], "Name"]
    if vendor_name.empty:
        send_email(
            "Invalid vendor",
            f"Vendor {df.iloc[0]['B']} is not valid because it does not match the expected NIF number in our database"
        )
        return False

    vendor_No = vendors_df.loc[vendors_df["Name"] == vendor_name.iloc[0], "No_"]

    df["Emitente"] = vendor_name.iloc[0]
    df["Vendor No_"] = vendor_No.iloc[0]

    return df


def validate_total_invoice(df, response):
    """Validates and processes invoice totals by tax rate
    
    Args:
        df (pd.DataFrame): DataFrame containing raw invoice data
        response (dict): Email processing response containing sender details
        
    Returns:
        pd.DataFrame: Processed invoice data with tax breakdowns
        bool: False if validation fails
        
    Tax Rates:
        - I2: No VAT (0%)
        - I3/I4: 6% VAT
        - I5/I6: 13% VAT
        - I7/I8: 23% VAT
    """
    tax_columns = {
        'I2': None,    # No VAT
        'I3': 'I4',    # 6% VAT
        'I5': 'I6',    # 13% VAT
        'I7': 'I8'     # 23% VAT
    }
    
    present_columns = [col for col in tax_columns.keys() if col in df.columns]
    if not present_columns:
        logging.warning(f"Invoice from {response['email_details']['sender']} has no valid tax columns")
        send_email(
            "Invoice without values",
            f"Invoice sent by {response['email_details']['sender']} is not valid - no tax values found"
        )
        return False

    result_df = pd.DataFrame(columns=[
        'Emitente', 'Nº Fatura / ATCUD', 'Tipo', 'Data Emissão',
        'Total', 'IVA', 'Base Tributável', 'Situação',
        'Comunicação Emitente', 'Comunicação Adquirente', 'Account'
    ])

    # Pega os valores de comunicação uma única vez
    comunicacao_emitente = str(df['I1'].iloc[0]) if 'I1' in df.columns and len(df['I1']) > 0 else ''
    comunicacao_adquirente = str(df['I1'].iloc[1]) if 'I1' in df.columns and len(df['I1']) > 1 else ''

    for base_col, vat_col in tax_columns.items():
        if base_col not in df.columns:
            continue
            
        base_value = df[base_col].iloc[0]
        if pd.isna(base_value) or base_value == 0:
            continue

        try:
            # Converte o valor base para float
            base_amount = float(str(base_value).strip())
            
            # Processa o valor do IVA se existir
            vat_amount = 0
            if vat_col and vat_col in df.columns:
                vat_value = df[vat_col].iloc[0]
                if not pd.isna(vat_value):
                    vat_amount = float(str(vat_value).strip())

            # Só cria a linha se tiver um valor base maior que zero
            if base_amount > 0:
                new_row = pd.DataFrame({
                    'Emitente': [df['Emitente'].iloc[0]],
                    'Nº Fatura / ATCUD': [str(df['H'].iloc[0])],
                    'Tipo': [str(df['D'].iloc[0]) if 'D' in df.columns else ''],
                    'Data Emissão': [str(df['F'].iloc[0]) if 'F' in df.columns else ''],
                    'Total': [base_amount + vat_amount],
                    'IVA': [vat_amount],
                    'Base Tributável': [base_amount],
                    'Situação': ['Registrada'],
                    'Comunicação Emitente': [comunicacao_emitente],
                    'Comunicação Adquirente': [comunicacao_adquirente],
                    'Account': [df['Account'].iloc[0]]
                })
                
                if result_df.empty:
                    result_df = new_row
                else:
                    result_df = pd.concat([result_df, new_row], ignore_index=True)
            
        except (ValueError, TypeError) as e:
            logging.error(f"Error processing values for column {base_col}: {str(e)}")
            logging.error(f"Base value: {base_value}, VAT value: {df[vat_col].iloc[0] if vat_col else 'None'}")
            continue

    if result_df.empty:
        logging.warning(f"No valid tax values found in invoice from {response['email_details']['sender']}")
        send_email(
            "Invoice without values",
            f"Invoice sent by {response['email_details']['sender']} is not valid - no valid tax values found"
        )
        return False

    return result_df


def process_df(response):
    """Processes invoice data from QR code response
    
    Args:
        response (dict): Email processing response containing:
            - email_details: Email metadata
            - qr_info: QR code content
            
    Returns:
        pd.DataFrame: Processed invoice data
        bool: False if processing fails
    """
    if not isinstance(response, dict):
        logging.error("Invalid response format")
        send_email(
            "Error in processing",
            "The email details were not processed correctly."
        )
        return False

    qr_info = response.get("qr_info", "")
    pairs = qr_info.split('*')
    
    data = {
        column: [value] 
        for pair in pairs 
        if pair and len(pair.split(':')) == 2
        for column, value in [pair.split(':')]
    }
    
    df = pd.DataFrame(data)

    df = initial_validation(df, response)
    if not isinstance(df, pd.DataFrame):
        return False

    try:
        # Usa o Vendor No_ para buscar a conta
        account_vendor = fetch_account_vendor(df["Vendor No_"].iloc[0])
        
        # Processa a conta
        if len(account_vendor) > 1:
            account_number = send_message(response.get("email_details"), account_vendor)
        else:
            account_number = account_vendor["No_"].iloc[0]

        if not account_number:
            send_email(
                "Invalid account number",
                f"Invoice sent by {response['email_details']['sender']} is not valid - no valid account number found"
            )
            return False

        df = df.reset_index(drop=True).copy()
        account_values = [account_number] * len(df.index)
        
        df.loc[:, 'Account'] = account_values
        df = df.drop('Vendor No_', axis=1)

        result_df = validate_total_invoice(df, response)
        if not isinstance(result_df, pd.DataFrame):
            return False

        logging.info(f"Invoice processed successfully for {response['email_details']['sender']}")
        return result_df

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Erro processing invoice: {error_msg}")
        send_email(
            "Erro no processamento",
            f"Ocorreu um erro ao processar a fatura.\nErro: {error_msg}"
        )
        return False
