import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from config.navision_vendor_api import get_navision_vendors


def test_get_navision_vendors():
    print("\nStarting Navision vendors test...")
    try:
        print("Attempting to fetch vendors from Navision...")
        vendors = get_navision_vendors()

        # ✅ Basic checks
        print(f"Received response. Type: {type(vendors)}")
        assert isinstance(vendors, list), "Expected a list of vendor records"
        print(f"Number of vendors: {len(vendors)}")
        assert len(vendors) > 0, "No vendors returned from NAVISION"

        # ✅ Inspect the first record
        first = vendors[0]
        print(f"First vendor type: {type(first)}")
        assert isinstance(first, dict), "Each vendor should be a dictionary"
        assert "No" in first or "Name" in first, "Expected vendor fields missing"

        print(f"\n✅ Successfully fetched {len(vendors)} vendor(s)")
        print(f"First vendor: {first}\n")

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Test script starting...")
    test_get_navision_vendors()
    print("Test script completed.")
