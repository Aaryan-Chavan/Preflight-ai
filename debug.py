import sys
import os
import traceback

print("--- 1. Testing Import ---")
sys.path.insert(0, os.path.abspath("src"))
try:
    from preflight.storage.db import get_connection
    print("✅ Import succeeded!")
except Exception:
    traceback.print_exc()

print("\n--- 2. Reading DB Path Configuration ---")
try:
    with open(os.path.join("src", "preflight", "config", "paths.py"), "r") as f:
        print(f.read())
except Exception as e:
    print(f"Could not read paths.py: {e}")