import os
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Internal Imports
from agent import context, setup_identity, live_gmail_scan

mcp = FastMCP("GriefOS-Live")

@mcp.tool()
def tool_setup_identity(path: str) -> str:
    """Step 1: Parses Death Certificate. Use full path (C:/...)."""
    return setup_identity(path)

@mcp.tool()
def tool_live_scan() -> str:
    """Step 2: Deep scans Gmail bodies for actual financial data."""
    result = live_gmail_scan()
    if "Error" in result:
        return result
    
    found_assets = [f"{a.institution} ({a.asset_type})" for a in context.assets]
    return f"✅ Scan Complete. Found: {', '.join(found_assets) if found_assets else 'Nothing'}"

@mcp.tool()
def generate_bereavement_package() -> str:
    """Step 3: Finalizes the action plan."""
    if not context.identity:
        return "❌ Setup identity first."
    context.update_task("collect_dc", "completed")
    return f"📄 Package Ready for {context.identity.deceased_name}."

if __name__ == "__main__":
    mcp.run()