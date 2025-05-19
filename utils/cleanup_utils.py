# utils/cleanup_utils.py
import os
import shutil

def clean_pycache(project_root: str) -> None:
    """
    Walk `project_root`, delete every __pycache__ directory found.
    """
    for root, dirs, _ in os.walk(project_root):
        for d in dirs:
            if d == "__pycache__":
                full_path = os.path.join(root, d)
                shutil.rmtree(full_path)
                print(f"🩹 Removed cache: {full_path}")
