import pandas as pd
import os
from datetime import datetime

DEBUG_DIR = "data/debug"
os.makedirs(DEBUG_DIR, exist_ok=True)

def debug_save_df(df: pd.DataFrame, name: str):
    """
    Saves a DataFrame as a CSV file in the debug folder with a timestamp.

    Args:
        df (pd.DataFrame): The dataframe to save
        name (str): A short name to identify the dataframe
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.csv"
        path = os.path.join(DEBUG_DIR, filename)
        print(f"[DEBUG] Attempting to save to: {os.path.abspath(path)}")
        df.to_csv(path, index=False)
        print(f"[DEBUG] Successfully saved {name} DataFrame to {path}")
    except Exception as e:
        print(f"[ERROR] Failed to save DataFrame: {str(e)}")

def debug_log_gpt_input(vendor_no: str, prompt: str):
    """
    Saves the GPT input prompt to a text file for debugging.

    Args:
        vendor_no (str): Vendor identifier to tag the file
        prompt (str): The prompt sent to GPT
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gpt_prompt_{vendor_no}_{timestamp}.txt"
        path = os.path.join(DEBUG_DIR, filename)
        print(f"[DEBUG] Attempting to save to: {os.path.abspath(path)}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"[DEBUG] Successfully saved GPT prompt to {path}")
    except Exception as e:
        print(f"[ERROR] Failed to save GPT prompt: {str(e)}")

