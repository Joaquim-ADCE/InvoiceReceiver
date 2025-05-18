import os
import sys
from pathlib import Path
import pandas as pd

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)

from config.navision_api import get_full_registered_invoices

# Fetch all registered invoices (merged lines and headers)
df = get_full_registered_invoices()

# Keep only rows where Buy_from_Vendor_No is present
df = df[df['Buy_from_Vendor_No'].notna() & df['Buy_from_Vendor_No'].ne("")]

# Select relevant columns
columns_to_show = ['Document_No', 'Buy_from_Vendor_No', 'No_line', 'Description']
cleaned_df = df[columns_to_show]

# Print first 5 rows
print(cleaned_df.head())
