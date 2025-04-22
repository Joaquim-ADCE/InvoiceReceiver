import pandas as pd
from ProcessingData.API.navision_post_data import send_header_to_navision, send_line_to_navision
from ProcessingData.transformations.transformations import transform_data
import logging


def process_invoice(invoice_df, vendors_df, purchase_header_df, purchase_header_reg_df):
    """This function processes the invoice data and sends it to Navision
    Steps:
        1. Transform the data
        2. Validate all data before sending
        3. Send header and lines only if everything is valid
    Args:
        invoice_df (pd.DataFrame): DataFrame containing invoice data
        vendors_df (pd.DataFrame): DataFrame containing vendor information
        purchase_header_df (pd.DataFrame): DataFrame with purchase headers
        purchase_header_reg_df (pd.DataFrame): DataFrame with registered purchase headers
        
    Raises:
        Exception: If processing or sending to Navision fails
    """
    try:
        header_df, line_df = transform_data(invoice_df, vendors_df, purchase_header_df, purchase_header_reg_df)
        if header_df is False:
            return False
            
        line_df['Type'] = "G/L Account"
        line_df['FilteredTypeField'] = "G/L Account"
        line_df['No'] = line_df['Account']
        line_df = line_df.drop('Account', axis=1)
        
        successful_invoices = []
        failed_invoices = []
        
        # Processa cada fatura separadamente
        for _, header_row in header_df.iterrows():
            try:
                invoice_no = header_row["No_"]
                invoice_lines = line_df[line_df["Document_No"] == invoice_no]
                
                if invoice_lines.empty:
                    logging.error(f"No lines found for invoice {invoice_no}")
                    failed_invoices.append({"no": invoice_no, "error": "No lines found"})
                    continue
                
                # Prepara o payload do header
                header_payload = {
                    "Document_Type": str(header_row["Document Type"]),
                    "No": str(header_row["No_"]), 
                    "Buy_from_Vendor_No": str(header_row["Buy-from Vendor No_"]),
                    "Document_Date": header_row["Document Date"].strftime("%Y-%m-%d"),
                    "Vendor_Invoice_No": str(header_row["Vendor Invoice No_"])
                }
                header_payload = {k: v for k, v in header_payload.items() if v}
                
                # Prepara todos os payloads das linhas
                line_payloads = []
                line_no = 10000
                
                for _, line_row in invoice_lines.iterrows():
                    try:
                        if not str(line_row["Document_No"]).startswith('F'):
                            line_payload = {
                                "Document_Type": str(line_row["Document Type"]),
                                "Document_No": str(line_row["Document_No"]),
                                "Line_No": line_no,
                                "Quantity": float(line_row["Quantity"]),
                                "Direct_Unit_Cost": float(line_row["Direct_Unit_Cost"]),
                                "Total_VAT_Amount": float(line_row["Total_VAT_Amount"]),
                                "Type": str(line_row["Type"]),
                                "FilteredTypeField": str(line_row["FilteredTypeField"]),
                                "No": str(line_row["No"]),
                                "VAT_Prod_Posting_Group": str(line_row["VAT_Prod_Posting_Group"]),
                                "Withholding_Tax_Code": str(line_row["Withholding_Tax_Code"])
                            }
                        else:
                            line_payload = {
                                "Document_Type": str(line_row["Document Type"]),
                                "Document_No": str(line_row["Document_No"]),
                                "Line_No": line_no,
                                "Quantity": float(line_row["Quantity"]),
                                "Direct_Unit_Cost": float(line_row["Direct_Unit_Cost"]),
                                "Total_VAT_Amount": float(line_row["Total_VAT_Amount"]),
                                "Type": str(line_row["Type"]),
                                "FilteredTypeField": str(line_row["FilteredTypeField"]),
                                "No": str(line_row["No"]),
                                "VAT_Prod_Posting_Group": str(line_row["VAT_Prod_Posting_Group"])
                            }
                        line_payload = {k: v for k, v in line_payload.items() if v}
                        line_payloads.append((line_no, line_payload))
                        line_no += 10000
                    except Exception as e:
                        logging.error(f"Error preparing line payload for invoice {invoice_no}: {str(e)}")
                        raise
                
                # Se chegou até aqui, todos os payloads foram preparados com sucesso
                # Agora podemos enviar o header e as linhas
                
                # Primeiro envia o header
                send_header_to_navision(header_payload)
                logging.info(f"Header sent successfully: {invoice_no}")
                
                # Depois envia todas as linhas
                for line_no, line_payload in line_payloads:
                    send_line_to_navision(line_payload)
                    logging.info(f"Line sent successfully: {invoice_no} - {line_no}")
                
                successful_invoices.append(invoice_no)
                
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Error processing invoice {invoice_no}: {error_msg}")
                failed_invoices.append({"no": invoice_no, "error": error_msg})
                continue
        
        if failed_invoices:
            logging.warning(f"Some invoices failed to process: {failed_invoices}")
            
        if not successful_invoices:
            logging.error("No invoices were processed successfully")
            return False
            
        return True

    except Exception as e:
        logging.error(f"Error processing invoices: {str(e)}")
        raise e
