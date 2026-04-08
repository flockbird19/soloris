import re, os, pytesseract, base64
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from pydantic import BaseModel
from typing import Optional, List, Dict

pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

class DeathCertificateData(BaseModel):
    deceased_name: str
    date_of_death: str
    registration_number: str
    raw_text: str

class DocumentParser:
    def parse_file(self, file_path: str) -> DeathCertificateData:
        clean_path = file_path.strip().replace('"', '').replace("'", "")
        if clean_path.lower().endswith('.pdf'):
            text = self._extract_from_pdf(clean_path)
        else:
            text = self._extract_from_image(clean_path)
        return self._extract_structured_data(text)

    def _extract_from_pdf(self, path: str) -> str:
        try:
            reader = PdfReader(path)
            text = "".join([page.extract_text() or "" for page in reader.pages])
            if not text.strip():
                images = convert_from_path(path)
                text = "".join([pytesseract.image_to_string(img) for img in images])
            return text
        except: return ""

    def _extract_from_image(self, path: str) -> str:
        return pytesseract.image_to_string(Image.open(path))

    def _extract_structured_data(self, text: str) -> DeathCertificateData:
        name = re.search(r"Name\s*(?:of\s*(?:the\s*)?Deceased)?[:\s]+([A-Z\s\.]+)", text, re.I)
        dod = re.search(r"Date\s*(?:of\s*Death)?[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text, re.I)
        reg = re.search(r"(?:Registration|Reg)\s*No\.?[:\s]+([A-Z0-9/-]+)", text, re.I)
        return DeathCertificateData(
            deceased_name=name.group(1).strip().title() if name else "Unknown Deceased",
            date_of_death=dod.group(1) if dod else "Unknown Date",
            registration_number=reg.group(1) if reg else "Unknown Reg",
            raw_text=text
        )

class EmailAssetScanner:
    def scan_text(self, text: str) -> List[Dict]:
        found = []
        patterns = {
            "banking": (r"(HDFC|Bank|Account|Statement|Transaction|Loan)", "HDFC Bank"),
            "insurance": (r"(LIC|Policy|Insurance|Life)", "LIC India"),
            "epfo": (r"(EPF|UAN|Provident|Deposit)", "EPFO India"),
            "tax": (r"[A-Z]{5}[0-9]{4}[A-Z]{1}", "Income Tax Dept (PAN Found)")
        }
        for a_type, (regex, inst) in patterns.items():
            match = re.search(regex, text, re.I)
            if match:
                found.append({"type": a_type, "institution": inst, "id": match.group(0) if a_type == "tax" else "Detected in Body"})
        return found

class SubscriptionManager:
    def __init__(self):
        self.services = {
            "Netflix": ["netflix"], 
            "Spotify": ["spotify"], 
            "Gym": ["gym", "membership", "sanjana"],
            "Prime": ["amazon", "prime"]
        }

    def scan_for_subscriptions(self, text: str) -> List[str]:
        detected = []
        for service, keywords in self.services.items():
            if any(k.lower() in text.lower() for k in keywords):
                detected.append(service)
        return list(set(detected))

class RequirementEngine:
    def __init__(self):
        self.registry = {
            "banking": ["Original Death Certificate", "Claimant KYC", "Succession Certificate"],
            "insurance": ["Original Policy Bond", "Certified Death Cert", "Discharge Form"],
            "epfo": ["UAN Number", "Form 20", "Form 10D", "Nominee Aadhaar"],
            "tax": ["PAN Card Copy", "Legal Heir Certificate", "Letter to AO"]
        }
    def get_docs(self, asset_type: str) -> List[str]:
        return self.registry.get(asset_type.lower(), ["Death Certificate", "Claimant ID"])

class FormFiller:
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_checklist(self, task_name: str, documents: List[str]) -> str:
        content = f"📋 CHECKLIST: {task_name}\n" + "="*30 + "\n" + "\n".join([f"[ ] {d}" for d in documents])
        filename = f"Checklist_{task_name.replace(' ', '_')}.txt"
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f: f.write(content)
        return path

class LogisticsManager:
    def calculate_photocopy_needs(self, tasks: List) -> str:
        pending = [t for t in tasks if t.status != "completed"]
        count = len(pending) * 2
        return f"📋 LOGISTICS SUMMARY\n--------------------------\nTotal Unlocked Tasks: {len(pending)}\nRequired Death Cert Copies: {count}\nRequired ID Proof Copies: {count}\n💡 Pro-tip: Carry a physical folder for these documents."