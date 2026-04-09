import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# AI SDK
import anthropic

# Internal Logic
from agent import context, setup_identity, live_gmail_scan

# Ensure .env is loaded at the very start
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

def get_llm_decision(prompt: str):
    """
    Handles communication with Claude 3.5 Sonnet.
    """
    # 1. Fetch Key inside function to prevent initialization errors
    api_key = os.getenv("CLAUDE_KEY")
    
    if not api_key:
        print("❌ CRITICAL ERROR: 'CLAUDE_KEY' is missing from .env file!")
        return "ERROR_NO_KEY"

    # 2. Define the System Prompt
    sys_msg = f"""
    You are GriefOS, an AI executor for bereavement tasks. 
    Current Deceased: {context.identity.deceased_name if context.identity else 'None'}
    
    INSTRUCTIONS:
    - If user wants to find bank accounts, assets, or scan emails: reply ONLY 'TRIGGER_SCAN'.
    - If user mentions the uploaded file or identity details: reply ONLY 'TRIGGER_PARSE'.
    - Otherwise: provide a supportive, 1-sentence response.
    """
    
    try:
        # 3. Initialize Client and Request
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=100,
            system=sys_msg,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.upper()
    except Exception as e:
        print(f"❌ Claude API Error: {e}")
        return "ERROR_FETCHING_DECISION"

# --- UI ROUTES ---

@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "identity_uploaded": context.identity is not None, 
        "identity_data": context.identity,
        "deceased_name": context.identity.deceased_name if context.identity else None,
        "assets": context.assets, 
        "tasks": context.tasks
    })

@app.get("/identity")
async def identity_page(request: Request):
    return templates.TemplateResponse(request=request, name="identity.html", context={
        "identity_data": context.identity,
        "identity_uploaded": context.identity is not None
    })

@app.get("/assets")
async def assets_page(request: Request):
    return templates.TemplateResponse(request=request, name="assets.html", context={"assets": context.assets})

@app.get("/tasks")
async def tasks_page(request: Request):
    return templates.TemplateResponse(request=request, name="tasks.html", context={"tasks": context.tasks})

# --- ACTION ROUTES ---

@app.post("/agent-execute")
async def agent_execute(user_input: str = Form(...)):
    # Get AI decision
    decision = get_llm_decision(user_input)
    print(f"🤖 Claude Decision: {decision}")
    
    # Tool Execution Logic
    if "TRIGGER_SCAN" in decision: 
        print("🚀 Executing Gmail Scan...")
        live_gmail_scan()
    elif "TRIGGER_PARSE" in decision:
        print("🚀 Executing Document Parse...")
        files = list(UPLOAD_FOLDER.glob("*"))
        if files:
            setup_identity(str(files[-1]))
            
    return RedirectResponse(url="/", status_code=303)

@app.post("/upload-identity")
async def handle_upload(file: UploadFile = File(...)):
    path = UPLOAD_FOLDER / file.filename
    with open(path, "wb") as f: 
        shutil.copyfileobj(file.file, f)
    setup_identity(str(path))
    return RedirectResponse(url="/", status_code=303)

@app.post("/run-scan")
async def handle_manual_scan():
    live_gmail_scan()
    return RedirectResponse(url="/", status_code=303)