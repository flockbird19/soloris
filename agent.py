import logging
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel
from pathlib import Path
from tools import DeathCertificateData, RequirementEngine, DocumentParser, FormFiller, LLMAssetScanner
from gmail_auth import get_gmail_service

class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    
    def __str__(self):
        return str(self.value)

# Init Shared Tools
parser = DocumentParser()
llm_scanner = LLMAssetScanner()
engine = RequirementEngine()

class AssetInfo(BaseModel):
    asset_type: str
    institution: str
    account_number: Optional[str] = None

class TaskInfo(BaseModel):
    task_id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = []
    required_docs: List[str] = []

class GlobalContext:
    def __init__(self):
        self.identity: Optional[DeathCertificateData] = None
        self.assets: List[AssetInfo] = []
        self.tasks: List[TaskInfo] = []
        self.completed_tasks: List[str] = []

    def set_identity(self, data: DeathCertificateData): 
        self.identity = data
        # If the collect_dc task exists, mark it as completed since we just uploaded it
        self.update_task("collect_dc", TaskStatus.COMPLETED)

    def add_asset(self, asset: AssetInfo):
        if not any(a.institution.upper() == asset.institution.upper() for a in self.assets):
            self.assets.append(asset)

    def update_task(self, task_id: str, status: TaskStatus):
        for t in self.tasks:
            if t.task_id == task_id:
                t.status = status
                if status == TaskStatus.COMPLETED and task_id not in self.completed_tasks: 
                    self.completed_tasks.append(task_id)
        self._unlock()

    def _unlock(self):
        for t in self.tasks:
            if t.status == TaskStatus.BLOCKED and all(d in self.completed_tasks for d in t.dependencies):
                t.status = TaskStatus.PENDING

    def auto_populate_requirements(self, engine_ref: RequirementEngine, subscriptions: List[str]):
        dc_status = TaskStatus.COMPLETED if self.identity else TaskStatus.PENDING
        if not any(t.task_id == "collect_dc" for t in self.tasks):
            self.tasks.append(TaskInfo(task_id="collect_dc", title="Collect Death Certificate", status=dc_status))
            if dc_status == TaskStatus.COMPLETED and "collect_dc" not in self.completed_tasks:
                self.completed_tasks.append("collect_dc")
                
        for a in self.assets:
            # Only add task if it doesn't already exist
            if not any(t.task_id == f"claim_{a.institution}" for t in self.tasks):
                self.tasks.append(TaskInfo(task_id=f"claim_{a.institution}", title=f"Claim {a.institution}", 
                                         status=TaskStatus.BLOCKED, dependencies=["collect_dc"], required_docs=engine_ref.get_docs(a.asset_type)))
        for s in subscriptions:
            if not any(t.task_id == f"cancel_{s.lower()}" for t in self.tasks):
                self.tasks.append(TaskInfo(task_id=f"cancel_{s.lower()}", title=f"Cancel {s}", status=TaskStatus.PENDING))
                
        self._unlock()

def setup_identity(context: GlobalContext, path: str) -> str:
    try:
        identity_data = parser.parse_file(path)
        context.set_identity(identity_data)
        return f"✅ Verified: {identity_data.deceased_name}"
    except Exception as e:
        logging.error(f"Error setting up identity: {e}")
        return f"❌ Error: {str(e)}"

def live_gmail_scan(context: GlobalContext) -> str:
    try:
        service = get_gmail_service()
        # Scoped query: Only major financial domains, last 5 years
        query = "newer_than:5y"
        results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
        messages = results.get('messages', [])
        context.assets = []
        all_subs = []
        snippets = []
        
        keywords = ["account", "statement", "ending in", "policy", "premium", "balance", "folio", "subscription", "netflix", "spotify", "prime", "membership", "renew"]
        
        for msg in messages:
            full = service.users().messages().get(userId='me', id=msg['id']).execute()
            body = llm_scanner.decode_gmail_body(full.get('payload', {})) or full.get('snippet', '')
            
            body_lower = body.lower()
            if any(k in body_lower for k in keywords):
                snippets.append(body[:600])
                
        if snippets:
            extracted_assets = llm_scanner.extract_assets(snippets)
            for a in extracted_assets:
                atype = a.get('type', 'banking')
                if atype == 'subscription':
                    all_subs.append(a.get('institution', 'Unknown'))
                else:
                    context.add_asset(AssetInfo(
                        asset_type=atype, 
                        institution=a.get('institution', 'Unknown'), 
                        account_number=a.get('id', 'Unknown')
                    ))
                    
        # Update Context Tasks
        context.auto_populate_requirements(engine, list(set(all_subs)))
        return "✅ Scan Complete"
    except Exception as e:
        logging.error(f"Error during Gmail scan: {e}")
        return f"❌ Error: {str(e)}"