import os
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import os

# Get the directory where mcp_server.py actually lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Use this for all your file loading
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Example: If you load credentials in gmail_auth.py, use:
# creds_path = os.path.join(BASE_DIR, 'credentials.json')
# Internal Imports
from tools import DocumentParser, EmailAssetScanner, FormFiller, RequirementEngine, SubscriptionManager, LogisticsManager
from agent import context, AssetInfo, TaskInfo
from gmail_auth import get_gmail_service

# Load environment variables from .env
load_dotenv()

# --- API KEY ROTATION LOGIC ---
class KeyRotator:
    def __init__(self):
        self.keys = []
        i = 1
        while True:
            k = os.getenv(f"API_KEY_{i}")
            if not k: break
            self.keys.append(k)
            i += 1
        
        if not self.keys:
            print("⚠️ WARNING: No API_KEY_N found in .env file.")

    def call_with_failover(self, func, *args, **kwargs):
        """Tries a function with every key until one works."""
        last_exception = None
        for key in self.keys:
            try:
                # We pass the current key to the function as 'api_key'
                return func(*args, **kwargs, api_key=key)
            except Exception as e:
                print(f"⚠️ Key failed, rotating... Error: {e}")
                last_exception = e
                continue
        
        # If we have no keys at all, just try the function once normally
        if not self.keys:
            return func(*args, **kwargs)
            
        raise Exception(f"❌ All {len(self.keys)} keys failed. Last error: {last_exception}")

# 1. Initialize FastMCP & Rotator
mcp = FastMCP("GriefOS-Live")
rotator = KeyRotator()

# 2. Initialize Tools
parser, scanner, filler = DocumentParser(), EmailAssetScanner(), FormFiller()
engine, sub_manager, logistics = RequirementEngine(), SubscriptionManager(), LogisticsManager()

# --- MCP TOOLS ---

@mcp.tool()
def setup_identity(path: str) -> str:
    """Step 1: Ingests the Death Certificate and sets context."""
    clean_path = path.strip().replace('"', '').replace("'", "")
    
    if not os.path.exists(clean_path):
        return f"❌ File not found at: {clean_path}. Use an absolute path."

    try:
        identity_data = parser.parse_file(clean_path)
        context.set_identity(identity_data)
        return f"✅ Identity Verified: {identity_data.deceased_name}."
    except Exception as e:
        return f"❌ Parsing Error: {str(e)}"

@mcp.tool()
def live_gmail_scan() -> str:
    """Step 2: Scans Gmail with API key failover logic."""
    
    def scan_logic(api_key=None):
        # Even if get_gmail_service uses credentials.json, 
        # this block now supports any secondary API needs via 'api_key'
        service = get_gmail_service()
        query = "HDFC OR LIC OR EPFO OR Netflix OR Spotify OR Amazon"
        results = service.users().messages().list(userId='me', q=query, maxResults=15).execute()
        messages = results.get('messages', [])
        
        if not messages: return "🔍 No relevant emails found."

        found_assets = 0
        detected_subs = []

        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id'], format='minimal').execute()
            text = m.get('snippet', '')
            
            for a in scanner.scan_text(text):
                context.add_asset(AssetInfo(asset_type=a['type'], institution=a['institution'], account_number=a['id']))
                found_assets += 1
            
            detected_subs.extend(sub_manager.scan_for_subscriptions(text))

        context.tasks = [TaskInfo(task_id="collect_dc", title="Collect Death Certificate")]
        context.auto_populate_requirements(engine, list(set(detected_subs)))
        
        return f"🔍 Scan Complete: {found_assets} assets, {len(set(detected_subs))} subs found."

    # Execute the scan using the rotator
    try:
        return rotator.call_with_failover(scan_logic)
    except Exception as e:
        return str(e)

@mcp.tool()
def generate_bereavement_package() -> str:
    """Step 3: Generates final checklists and summary."""
    if not context.identity:
        return "❌ Error: Identity not set. Run setup_identity first."

    context.update_task("collect_dc", "completed")
    
    legal_tasks = [t for t in context.tasks if "claim" in t.task_id]
    for task in legal_tasks:
        if task.required_docs:
            filler.generate_checklist(task.title, task.required_docs)
            
    report = [f"📄 Success: Generated {len(legal_tasks)} checklists in /outputs.\n"]
    
    subs = [t for t in context.tasks if "cancel" in t.task_id]
    if subs:
        report.append("🚫 SUBSCRIPTIONS:")
        for s in subs: report.append(f"- {s.title}")
    
    report.append(f"\n{logistics.calculate_photocopy_needs(context.tasks)}")
    
    return "\n".join(report)

if __name__ == "__main__":
    mcp.run()