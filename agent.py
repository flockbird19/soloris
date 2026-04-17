import logging
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel
from pathlib import Path
from tools import DeathCertificateData, RequirementEngine, DocumentParser, EmailAssetScanner, SubscriptionManager, FormFiller
from gmail_auth import get_gmail_service

class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    BLOCKED = "blocked"

# Init Shared Tools
parser = DocumentParser()
scanner = EmailAssetScanner()
engine = RequirementEngine()
sub_manager = SubscriptionManager()

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

    def set_identity(self, data: DeathCertificateData): self.identity = data
    def add_asset(self, asset: AssetInfo):
        if not any(a.institution == asset.institution for a in self.assets):
            self.assets.append(asset)

    def update_task(self, task_id: str, status: TaskStatus):
        for t in self.tasks:
            if t.task_id == task_id:
                t.status = status
                if status == TaskStatus.COMPLETED: self.completed_tasks.append(task_id)
        self._unlock()

    def _unlock(self):
        for t in self.tasks:
            if t.status == TaskStatus.BLOCKED and all(d in self.completed_tasks for d in t.dependencies):
                t.status = TaskStatus.PENDING

    def auto_populate_requirements(self, engine_ref: RequirementEngine, subscriptions: List[str]):
        if not any(t.task_id == "collect_dc" for t in self.tasks):
            self.tasks.append(TaskInfo(task_id="collect_dc", title="Collect Death Certificate", status=TaskStatus.PENDING))
        for a in self.assets:
            self.tasks.append(TaskInfo(task_id=f"claim_{a.institution}", title=f"Claim {a.institution}", 
                                     status=TaskStatus.BLOCKED, dependencies=["collect_dc"], required_docs=engine_ref.get_docs(a.asset_type)))
        for s in subscriptions:
            self.tasks.append(TaskInfo(task_id=f"cancel_{s.lower()}", title=f"Cancel {s}", status=TaskStatus.PENDING))

context = GlobalContext()

def setup_identity(path: str) -> str:
    try:
        identity_data = parser.parse_file(path)
        context.set_identity(identity_data)
        return f"✅ Verified: {identity_data.deceased_name}"
    except Exception as e:
        logging.error(f"Error setting up identity: {e}")
        return f"❌ Error: {str(e)}"

def live_gmail_scan() -> str:
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', q="Bank OR Insurance OR Statement", maxResults=10).execute()
        messages = results.get('messages', [])
        context.assets = []
        all_subs = []
        for msg in messages:
            full = service.users().messages().get(userId='me', id=msg['id']).execute()
            body = scanner.decode_gmail_body(full.get('payload', {})) or full.get('snippet', '')
            for a in scanner.scan_text(body):
                context.add_asset(AssetInfo(asset_type=a['type'], institution=a['institution'], account_number=a['id']))
            all_subs.extend(sub_manager.scan_for_subscriptions(body))
        context.auto_populate_requirements(engine, list(set(all_subs)))
        return "✅ Scan Complete"
    except Exception as e:
        logging.error(f"Error during Gmail scan: {e}")
        return f"❌ Error: {str(e)}"