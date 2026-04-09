import os
from pathlib import Path
from mcp_server import setup_identity, live_gmail_scan, generate_bereavement_package
from agent import context

# 1. SETUP TEST DATA
# Use the same path you've been trying in Claude
TEST_CERT_PATH = r"C:/Users/HP/Documents/soloris/data/uploads/death_certificate.pdf"

def run_pipeline_test():
    print("🚀 STARTING FULL PIPELINE TEST\n" + "="*30)

    # --- STEP 1: IDENTITY ---
    print("\n[Step 1] Testing setup_identity...")
    identity_res = setup_identity(TEST_CERT_PATH)
    print(f"Result: {identity_res}")
    
    if "✅" not in identity_res:
        print("❌ Pipeline stopped: Identity verification failed.")
        return

    # --- STEP 2: GMAIL SCAN ---
    print("\n[Step 2] Testing live_gmail_scan...")
    # This will trigger the deep body scan logic we wrote
    scan_res = live_gmail_scan()
    print(f"Result:\n{scan_res}")

    # --- STEP 3: PACKAGE GENERATION ---
    print("\n[Step 3] Testing generate_bereavement_package...")
    package_res = generate_bereavement_package()
    print(f"Result:\n{package_res}")

    # --- STEP 4: FILE SYSTEM VERIFICATION ---
    print("\n[Step 4] Verifying Output Files...")
    output_dir = Path(__file__).resolve().parent / "outputs"
    if output_dir.exists():
        files = list(output_dir.glob("*.txt"))
        print(f"✅ Found {len(files)} checklists in {output_dir}")
        for f in files:
            print(f"  - {f.name}")
    else:
        print("❌ Error: 'outputs' directory was not created.")

    print("\n" + "="*30 + "\n✅ PIPELINE TEST COMPLETE")

if __name__ == "__main__":
    run_pipeline_test()