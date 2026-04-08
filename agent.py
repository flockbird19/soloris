from typing import List, Optional
from pydantic import BaseModel
from tools import DeathCertificateData, RequirementEngine

class AssetInfo(BaseModel):
    asset_type: str
    institution: str
    account_number: Optional[str] = None

class TaskInfo(BaseModel):
    task_id: str
    title: str
    status: str = "pending"
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

    def add_asset(self, asset: AssetInfo):
        if not any(a.institution == asset.institution for a in self.assets):
            self.assets.append(asset)

    def update_task(self, task_id: str, status: str):
        for t in self.tasks:
            if t.task_id == task_id:
                t.status = status
                if status == "completed" and task_id not in self.completed_tasks:
                    self.completed_tasks.append(task_id)
        self._unlock()

    def _unlock(self):
        for t in self.tasks:
            if t.status == "blocked" and all(d in self.completed_tasks for d in t.dependencies):
                t.status = "pending"

    def get_next_tasks(self) -> List[TaskInfo]:
        return [t for t in self.tasks if t.status == "pending"]

    def auto_populate_requirements(self, engine: RequirementEngine, subscriptions: List[str]):
        if not any(t.task_id == "collect_dc" for t in self.tasks):
            self.tasks.append(TaskInfo(task_id="collect_dc", title="Collect Death Certificate", status="pending"))

        for a in self.assets:
            self.tasks.append(TaskInfo(
                task_id=f"claim_{a.institution.replace(' ', '_')}", 
                title=f"Claim {a.institution}",
                status="blocked", 
                dependencies=["collect_dc"], 
                required_docs=engine.get_docs(a.asset_type)
            ))
        for s in subscriptions:
            self.tasks.append(TaskInfo(task_id=f"cancel_{s.lower()}", title=f"Cancel {s} Subscription", status="pending"))

context = GlobalContext()
