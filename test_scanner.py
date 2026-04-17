from dotenv import load_dotenv
import logging
import json
from tools import LLMAssetScanner

# Load your API key from .env
load_dotenv(".env")
logging.basicConfig(level=logging.INFO)

scanner = LLMAssetScanner()

print("=========================================")
print("Testing LLM Asset Extraction Pipeline")
print("=========================================\n")

test_email = "Here is your latest HDFC bank statement. Your account number ending in 9876 has a balance of $50."
print(f"Simulating Email Body:\n\"{test_email}\"\n")

print("Sending to Claude 3.5 Sonnet for extraction...\n")
results = scanner.extract_assets([test_email])

print("--- Extraction Results ---")
if results:
    print(json.dumps(results, indent=2))
else:
    print("No assets found or extraction failed!")
    
print("\n=========================================")
