from pathlib import Path
import sys
import pandas as pd

project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)

from config.navision_api import get_full_registered_invoices

def debug_navision_merge():
    df = get_full_registered_invoices()
    print("✅ Columns in DataFrame:")
    print(df.columns.tolist())

if __name__ == "__main__":
    debug_navision_merge()

