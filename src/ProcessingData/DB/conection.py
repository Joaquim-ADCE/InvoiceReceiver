import pyodbc
import pandas as pd


SERVER = 'SRV004'
DATABASE = 'ADC'

connection = pyodbc.connect(
    f"DRIVER={{SQL Server}}; SERVER={SERVER}; DATABASE={DATABASE}; Trusted_Connection=yes"
)
cursor = connection.cursor()


def fetch_from_table(table, schema):
    """This function fetches data from a table
    Steps:
        1. Execute the query
        2. Fetch the data
        3. Convert the data to a DataFrame
    Args:
        table (str): The name of the table
        schema (str): The schema of the table
    Returns:
        pd.DataFrame: The data from the table
    """
    try:
        query = f"SELECT * FROM {schema}.{table}"
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        df = pd.DataFrame.from_records(rows, columns=columns)
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")


def fetch_account_vendor(vendor_id):
    """This function fetches the account vendor from the table
    Steps:
        1. Execute the query
        2. Fetch the data
        3. Convert the data to a DataFrame
    Args:
        vendor_id (str): The ID of the vendor
    Returns:
        pd.DataFrame: The data from the table
    """
    try:
        query = "SELECT No_, Description FROM ADC.dbo.[ADC$Purch_ Inv_ Line] WHERE [Buy-From Vendor No_] = ?"
        cursor.execute(query, (vendor_id,))
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        df = pd.DataFrame.from_records(rows, columns=columns)
        return df
    except Exception as e:
        print(f"Error fetching account vendor: {e}")
        return pd.DataFrame()
