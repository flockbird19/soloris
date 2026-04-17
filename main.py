import os
import shutil
import logging
import uuid
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

import json

# AI SDK
import anthropic

# Internal Logic
from agent import GlobalContext, setup_identity, live_gmail_scan, AssetInfo, TaskInfo
from tools import PDFGenerator, FormFiller, DeathCertificateData

# Ensure .env is loaded at the very start
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Initialize Tools
pdf_tool = PDFGenerator()
filler_tool = FormFiller()

# Session Management
contexts = {}

class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in contexts:
            session_id = str(uuid.uuid4())
            contexts[session_id] = GlobalContext()
            request.state.session_id = session_id
            response = await call_next(request)
            response.set_cookie("session_id", session_id, httponly=True)
            return response
        
        request.state.session_id = session_id
        return await call_next(request)

app.add_middleware(SessionMiddleware)

def get_context(request: Request) -> GlobalContext:
    return contexts[request.state.session_id]

def get_llm_decision(prompt: str, context: GlobalContext):
    """
    Handles communication with Claude 3.5 Sonnet.
    """
    api_key = os.getenv("CLAUDE_KEY")
    
    if not api_key:
        logging.error("CRITICAL ERROR: 'CLAUDE_KEY' is missing from .env file!")
        return "ERROR_NO_KEY"

    # 2. Define the System Prompt
    sys_msg = f"""
    You are GriefOS, an AI executor for bereavement tasks. 
    Current Deceased: {context.identity.deceased_name if context.identity else 'None'}
    
    INSTRUCTIONS:
    - If user wants to find bank accounts, assets, or scan emails: reply ONLY 'TRIGGER_SCAN'.
    - If user mentions the uploaded file or identity details: reply ONLY 'TRIGGER_PARSE'.
    - If user wants to download a checklist or PDF: reply ONLY 'TRIGGER_DOWNLOAD'.
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
        logging.error(f"Claude API Error: {e}")
        return "ERROR_FETCHING_DECISION"

# --- UI ROUTES ---

@app.get("/")
async def dashboard(request: Request, context: GlobalContext = Depends(get_context)):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "identity_uploaded": context.identity is not None, 
        "identity_data": context.identity,
        "deceased_name": context.identity.deceased_name if context.identity else None,
        "assets": context.assets, 
        "tasks": context.tasks
    })

@app.get("/fill-form/{task_id}/")
async def preview_form(request: Request, task_id: int, context: GlobalContext = Depends(get_context)):
    if not context.identity or not context.tasks:
        return RedirectResponse(url="/", status_code=303)
    
    try:
        current_task = context.tasks[task_id]
        task_title = current_task.title 
        
        form_preview = filler_tool.prepare_fill_data(context.identity, task_title)
        task_dict = current_task.dict() 
        return templates.TemplateResponse(
            request=request,
            name="form_preview.html", 
            context={
                "form": form_preview,
                "task": task_dict
            }
        )
    except IndexError:
        raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        logging.error(f"SYSTEM ERROR previewing form: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.get("/utility-letter/{task_id}/")
async def utility_letter(request: Request, task_id: int, context: GlobalContext = Depends(get_context)):
    if not context.identity or not context.tasks:
        return RedirectResponse(url="/", status_code=303)
    
    try:
        current_task = context.tasks[task_id]
        letter_data = filler_tool.prepare_letter_data(context.identity, current_task.title)
        
        return templates.TemplateResponse(
            request=request,
            name="letter_preview.html", 
            context={
                "letter": letter_data,
                "task": current_task.dict()
            }
        )
    except IndexError:
        raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        logging.error(f"Letter Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/privacy")
async def privacy_page(request: Request, context: GlobalContext = Depends(get_context)):
    return templates.TemplateResponse(request=request, name="privacy.html", context={})

@app.get("/identity")
async def identity_page(request: Request, context: GlobalContext = Depends(get_context)):
    return templates.TemplateResponse(request=request, name="identity.html", context={
        "identity_data": context.identity,
        "identity_uploaded": context.identity is not None
    })

@app.get("/assets")
async def assets_page(request: Request, context: GlobalContext = Depends(get_context)):
    return templates.TemplateResponse(request=request, name="assets.html", context={"assets": context.assets})

@app.get("/tasks")
async def tasks_page(request: Request, context: GlobalContext = Depends(get_context)):
    return templates.TemplateResponse(request=request, name="tasks.html", context={"tasks": context.tasks})

# --- NEW DOWNLOAD ROUTE ---
@app.get("/download-checklist")
async def download_checklist(context: GlobalContext = Depends(get_context)):
    if not context.identity:
        return RedirectResponse(url="/", status_code=303)
    
    file_relative_path = pdf_tool.create_checklist_pdf(
        context.identity.deceased_name, 
        context.tasks
    )
    
    full_path = BASE_DIR / file_relative_path.lstrip("/")
    return FileResponse(
        path=full_path, 
        filename=os.path.basename(full_path),
        media_type='application/pdf'
    )

# --- ACTION ROUTES ---
@app.get("/download-form/{task_id}")
async def download_filled_form(task_id: int, context: GlobalContext = Depends(get_context)):
    if not context.identity or not context.tasks:
        return RedirectResponse("/")
    
    current_task = context.tasks[task_id]
    task_title = current_task['title'] if isinstance(current_task, dict) else current_task.title
    
    form_data = filler_tool.prepare_fill_data(context.identity, task_title)
    file_url = filler_tool.generate_filled_pdf(form_data)
    
    return FileResponse(
        path=BASE_DIR / file_url.lstrip("/"), 
        filename=os.path.basename(file_url),
        media_type='application/pdf'
    )

@app.post("/agent-execute")
async def agent_execute(user_input: str = Form(...), context: GlobalContext = Depends(get_context)):
    user_input = user_input.lower()
    if "scan" in user_input or "mail" in user_input:
        return RedirectResponse(url="/scan-consent", status_code=303)
    elif "checklist" in user_input or "plan" in user_input:
        if not context.identity:
            raise HTTPException(status_code=400, detail="Identity missing")
        pdf_tool.create_checklist_pdf(context.identity.deceased_name, context.tasks)
        return RedirectResponse(url="/tasks", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/export-session")
async def export_session(context: GlobalContext = Depends(get_context)):
    data = {
        "identity": context.identity.dict() if context.identity else None,
        "assets": [a.dict() for a in context.assets],
        "tasks": [t.dict() for t in context.tasks],
        "completed_tasks": context.completed_tasks
    }
    file_path = BASE_DIR / "static" / "downloads" / "session_token.json"
    file_path.parent.mkdir(exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f)
    return FileResponse(path=file_path, filename="griefos_session.json", media_type='application/json')

@app.post("/import-session")
async def import_session(file: UploadFile = File(...), context: GlobalContext = Depends(get_context)):
    try:
        content = await file.read()
        data = json.loads(content)
        if data.get("identity"):
            context.identity = DeathCertificateData(**data["identity"])
        if data.get("assets"):
            context.assets = [AssetInfo(**a) for a in data["assets"]]
        if data.get("tasks"):
            context.tasks = [TaskInfo(**t) for t in data["tasks"]]
        if "completed_tasks" in data:
            context.completed_tasks = data["completed_tasks"]
    except Exception as e:
        logging.error(f"Error importing session: {e}")
    return RedirectResponse(url="/", status_code=303)

@app.post("/upload-identity")
async def handle_identity_upload(request: Request, file: UploadFile = File(...), context: GlobalContext = Depends(get_context)):
    try:
        file_path = UPLOAD_FOLDER / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        from tools import DocumentParser
        parser = DocumentParser()
        identity_data = parser.parse_file(str(file_path))
        
        return templates.TemplateResponse(request=request, name="review_identity.html", context={"identity_data": identity_data})
    except Exception as e:
        logging.error(f"Error handling upload: {e}")
        return RedirectResponse(url="/identity", status_code=303)

@app.post("/confirm-identity")
async def confirm_identity(
    deceased_name: str = Form(...),
    date_of_death: str = Form(...),
    registration_number: str = Form(...),
    aadhaar_number: str = Form(""),
    context: GlobalContext = Depends(get_context)
):
    data = DeathCertificateData(
        deceased_name=deceased_name,
        date_of_death=date_of_death,
        registration_number=registration_number,
        aadhaar_number=aadhaar_number,
        raw_text="Manually Confirmed"
    )
    context.set_identity(data)
    return RedirectResponse(url="/identity", status_code=303)

@app.post("/run-scan")
async def handle_manual_scan(context: GlobalContext = Depends(get_context)):
    return RedirectResponse(url="/scan-consent", status_code=303)

@app.get("/scan-consent")
async def scan_consent(request: Request, context: GlobalContext = Depends(get_context)):
    from gmail_auth import get_gmail_service
    try:
        service = get_gmail_service()
        query = "newer_than:5y"
        results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
        messages = results.get('messages', [])
        count = len(messages)
    except Exception as e:
        logging.error(f"Error fetching consent count: {e}")
        count = 0
    return templates.TemplateResponse(request=request, name="scan_consent.html", context={"count": count})

@app.post("/execute-scan")
async def execute_scan(context: GlobalContext = Depends(get_context)):
    live_gmail_scan(context)
    return RedirectResponse(url="/assets", status_code=303)