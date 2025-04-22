import pandas as pd
import numpy as np


def get_highest_invoice_number(purchase_header_df):
    """This function gets the highest invoice number and generates the next one
    Steps:
        1. Check if the purchase_header_df is empty or if the column 'No_' is not in the DataFrame
        2. If the DataFrame is empty or the column 'No_' is not in the DataFrame, return 1
        3. If the DataFrame is not empty and the column 'No_' is in the DataFrame, get the highest invoice number
        4. If the highest invoice number contains 'FCA25', split the number and add 1 to the number part
        5. If the highest invoice number does not contain 'FCA25', return 1
    Args:
        purchase_header_df (pd.DataFrame): DataFrame with the purchase header data
    Returns:
        int: The highest invoice number
    """
    try:
        if purchase_header_df.empty or 'No_' not in purchase_header_df.columns:
            return 1

        mask = purchase_header_df['No_'].str.contains('FCA25', na=False)
        filtered_df = purchase_header_df[mask]

        if filtered_df.empty:
            return 1

        highest_invoice_number = filtered_df['No_'].max()

        if 'FCA25' in highest_invoice_number:
            number_part = highest_invoice_number.split('FCA25')[1]
            try:
                return int(number_part) + 1
            except ValueError:
                return 1
        else:
            return 1

    except Exception as e:
        print(f"Error generating invoice number: {str(e)}")
        return 1


def transform_data(invoice_df, vendors_df, purchase_header_df, purchase_header_reg_df):
    """This function transforms the data
    Steps:
        1. Rename the column 'Nº Fatura / ATCUD' to 'Vendor Invoice No_'
        2. Convert the column 'Emitente' to uppercase
        3. Drop the column 'Emitente'
        4. Merge the invoice DataFrame with the vendor DataFrame on the column 'Name'
        5. Drop the rows where the column 'Vendor Invoice No_' is NaN
        6. Get the highest invoice number and generate the next one
        7. Create the header DataFrame
        8. Create the line DataFrame
        9. Validate the line DataFrame
    Args:
        invoice_df (pd.DataFrame): DataFrame with the invoice data
        vendors_df (pd.DataFrame): DataFrame with the vendor data
        purchase_header_df (pd.DataFrame): DataFrame with the purchase header data
        purchase_header_reg_df (pd.DataFrame): DataFrame with the purchase header registration data
    Returns:
        line_df (pd.DataFrame): DataFrame with the line data
        header_df (pd.DataFrame): DataFrame with the header data
    """
    invoice_df = invoice_df.rename(columns={'Nº Fatura / ATCUD': 'Vendor Invoice No_'})
    
    invoice_df['Name'] = invoice_df['Emitente'].str.upper()
    vendors_df['Name'] = vendors_df['Name'].str.upper()
    invoice_df = invoice_df.drop('Emitente', axis=1)

    merged_df = pd.merge(invoice_df, vendors_df, on='Name', how='left')
    merged_df = merged_df.dropna(subset=['VAT Registration No_'])

    unique_invoices = merged_df[
        ~merged_df['Vendor Invoice No_'].isin(purchase_header_df['Vendor Invoice No_']) &
        ~merged_df['Vendor Invoice No_'].isin(purchase_header_reg_df['Vendor Invoice No_'])
    ]
    if len(unique_invoices) == 0:
        return False, False


    invoice_number = get_highest_invoice_number(purchase_header_df)
    unique_invoices = unique_invoices.rename(columns={'No_': 'No__'})
    unique_invoices['No_'] = f'FCA25{str(invoice_number).zfill(6)}'

    header_df = create_header_df(unique_invoices)
    line_df = create_line_df(unique_invoices)
    
    valid_docs = line_df[line_df['VAT_Prod_Posting_Group'].notna()]['Document_No']
    header_df = header_df[header_df['No_'].isin(valid_docs)]
    line_df = line_df[line_df['Document_No'].isin(valid_docs)]

    return header_df, line_df


def create_header_df(unique_invoices):
    """This function creates the header DataFrame
    Steps:
        1. Create the header DataFrame
        2. Add the columns to the header DataFrame with the data from the unique_invoices DataFrame
    Args:
        unique_invoices (pd.DataFrame): DataFrame with unique invoices
    Returns:
        pd.DataFrame: DataFrame with the header information
    """
    header_df = pd.DataFrame()

    header_df['No_'] = unique_invoices['No_']
    header_df['Document Type'] = 'Invoice'
    header_df['Buy-from Vendor No_'] = unique_invoices['No__']
    header_df['Document Date'] = pd.to_datetime(unique_invoices['Data Emissão'], format='%Y%m%d')
    header_df['Vendor Invoice No_'] = unique_invoices['Vendor Invoice No_']

    return header_df


def create_line_df(unique_invoices):
    """This function creates the line DataFrame
    Steps:
        1. Create the line DataFrame
        2. Add the columns to the line DataFrame with the data from the unique_invoices DataFrame
        3. Calculate the direct unit cost
        4. Calculate the VAT amount
        5. Calculate the VAT percentage
        6. Set the VAT_Prod_Posting_Group based on the VAT percentage
        7. Add the Withholding Tax Code
    Args:
        unique_invoices (pd.DataFrame): DataFrame with unique invoices
    Returns:
        pd.DataFrame: DataFrame with the line information
    """
    line_df = pd.DataFrame()

    line_df['Document_No'] = unique_invoices['No_']
    line_df['Document Type'] = 'Invoice'
    line_df['Line_No'] = 10000
    line_df['Quantity'] = 1
    line_df['Account'] = unique_invoices['Account']

    line_df['Direct_Unit_Cost'] = (
        unique_invoices['Base Tributável']
        .astype(float)
    )

    iva = (
        unique_invoices['IVA']
        .astype(float)
    )

    line_df['Total_VAT_Amount'] = iva
    vat_percentage = (iva / line_df['Direct_Unit_Cost']) * 100

    mask = (vat_percentage.round(2) >= 22.99) & (vat_percentage.round(2) <= 23.01)
    line_df.loc[mask, 'VAT_Prod_Posting_Group'] = 'OBS-NOR'

    mask = (vat_percentage.round(2) >= 21.99) & (vat_percentage.round(2) <= 22.01)
    line_df.loc[mask, 'VAT_Prod_Posting_Group'] = 'OBS-NORMAD'

    mask = (vat_percentage.round(2) >= 5.99) & (vat_percentage.round(2) <= 6.01)
    line_df.loc[mask, 'VAT_Prod_Posting_Group'] = 'OBS-RDZ'

    mask = (vat_percentage.round(2) >= -0.01) & (vat_percentage.round(2) <= 0.01)
    line_df.loc[mask, 'VAT_Prod_Posting_Group'] = 'OBS-ISEN'

    line_df['Withholding_Tax_Code'] = np.where(
        unique_invoices['No_'].str.startswith('F'),
        'IRSINDEP23',
        ''
    )

    return line_df
