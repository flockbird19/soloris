import os
from mcp.server.fastmcp import FastMCP
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Import the corrected logic from your other files
from tools import DocumentParser, EmailAssetScanner, FormFiller, RequirementEngine, SubscriptionManager, LogisticsManager
from agent import context, AssetInfo, TaskInfo

# 1. Initialize FastMCP
mcp = FastMCP("GriefOS-Live")

# 2. Initialize Internal Tools
parser, scanner, filler = DocumentParser(), EmailAssetScanner(), FormFiller()
engine, sub_manager, logistics = RequirementEngine(), SubscriptionManager(), LogisticsManager()

# 3. Gmail OAuth Setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Handles secure OAuth2 login. Requires credentials.json."""
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return build('gmail', 'v1', credentials=creds)

# --- MCP TOOLS ---

@mcp.tool()
def setup_identity(path: str) -> str:
    """
    Step 1: Ingests the Death Certificate.
    Cleans the path and sets the global identity context.
    """
    # Defensive cleaning for Windows paths
    clean_path = path.strip().replace('"', '').replace("'", "")
    
    if not os.path.exists(clean_path):
        return f"❌ File not found at: {clean_path}"

    try:
        identity_data = parser.parse_file(clean_path)
        context.set_identity(identity_data)
        return f"✅ Identity Verified: Supporting the family of {identity_data.deceased_name}."
    except Exception as e:
        return f"❌ Error: {str(e)}"

@mcp.tool()
def live_gmail_scan() -> str:
    """
    Step 2: Scans live Gmail for financial assets and subscriptions.
    Automatically populates the bereavement roadmap.
    """
    try:
        service = get_gmail_service()
        query = "HDFC OR LIC OR EPFO OR Netflix OR Spotify OR Amazon"
        
        results = service.users().messages().list(userId='me', q=query, maxResults=15).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "🔍 Scan finished. No relevant financial footprints found."

        found_assets = 0
        detected_subs = []

        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id'], format='minimal').execute()
            text = m.get('snippet', '')
            
            # Find Banks/Insurance
            for a in scanner.scan_text(text):
                context.add_asset(AssetInfo(asset_type=a['type'], institution=a['institution'], account_number=a['id']))
                found_assets += 1
            
            # Find Subs
            detected_subs.extend(sub_manager.scan_for_subscriptions(text))

        # Core Task: Must collect the physical certificate first
        context.tasks = [TaskInfo(task_id="collect_dc", title="Collect Death Certificate")]
        
        # Build the roadmap
        context.auto_populate_requirements(engine, list(set(detected_subs)))
        
        return f"🔍 Scan Complete: Found {found_assets} assets and {len(set(detected_subs))} subscriptions."
    except Exception as e:
        return f"❌ Gmail Error: {str(e)}"

@mcp.tool()
def generate_bereavement_package() -> str:
    if not context.identity:
        return "❌ Error: Identity not set. Run setup_identity first."

    # Mark root task complete to unlock bank claims
    context.update_task("collect_dc", "completed")
    
    # Separate tasks for better presentation
    legal_claims = [t for t in context.tasks if "claim" in t.task_id]
    subscriptions = [t for t in context.tasks if "cancel" in t.task_id]
    
    # Generate files for legal claims
    for task in legal_claims:
        if task.required_docs:
            filler.generate_checklist(task.title, task.required_docs)
            
    # Build the final output string for the Inspector
    report = [f"📄 Success: Generated {len(legal_claims)} legal checklists in /outputs.\n"]
    
    if subscriptions:
        report.append("🚫 SUBSCRIPTIONS DETECTED (Action Required):")
        for s in subscriptions:
            report.append(f"- {s.title} (Status: Ready to cancel)")
    
    summary = logistics.calculate_photocopy_needs(context.tasks)
    report.append(f"\n{summary}")
    
    return "\n".join(report)

if __name__ == "__main__":
    mcp.run()
