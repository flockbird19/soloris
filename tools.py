import re
import os
import pytesseract
import base64
from pathlib import Path
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from pydantic import BaseModel
from typing import Optional, List, Dict

# Ensure Tesseract uses an absolute path
pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

class DeathCertificateData(BaseModel):
    deceased_name: str
    date_of_death: str
    registration_number: str
    aadhaar_number: Optional[str] = "Not Found" 
    raw_text: str

class DocumentParser:
    def parse_file(self, file_path: str) -> DeathCertificateData:
        file_obj = Path(file_path.strip().replace('"', '').replace("'", ""))
        if not file_obj.is_absolute():
            file_obj = file_obj.resolve()

        if file_obj.suffix.lower() == '.pdf':
            text = self._extract_from_pdf(str(file_obj))
        else:
            text = self._extract_from_image(str(file_obj))
            
        return self._extract_structured_data(text)

    def _extract_from_pdf(self, path: str) -> str:
        try:
            reader = PdfReader(path)
            text = "".join([page.extract_text() or "" for page in reader.pages])
            if not text.strip():
                images = convert_from_path(path)
                text = "".join([pytesseract.image_to_string(img) for img in images])
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    def _extract_from_image(self, path: str) -> str:
        try:
            return pytesseract.image_to_string(Image.open(path))
        except Exception as e:
            print(f"Error reading Image: {e}")
            return ""

    def _extract_structured_data(self, text: str) -> DeathCertificateData:
        # NAME: Captures name but stops at next major label
        name_pattern = r"(?:Name|Deceased Name)(?:\s+of\s+Deceased)?[:\s]+(.*?)(?=\s+(?:Date|Death|DOD|Reg|Place|Sex|Father|Mother|Aadhaar)|$)"
        name_match = re.search(name_pattern, text, re.I | re.DOTALL)
        raw_name = name_match.group(1).strip() if name_match else "Unknown Deceased"
        clean_name = re.sub(r"^(of\s+deceased|deceased|:)\s+", "", raw_name, flags=re.I).strip()

        # DOD: Multiline tolerant
        dod_match = re.search(r"(?:Date|Death|DOD)[:\s\n]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text, re.I)

        # REGISTRATION
        reg_match = re.search(r"(?:Registration|Reg|Certificate)\s*No\.?[:\s\n]+([A-Z0-9\s/-]+)", text, re.I)
        reg_val = reg_match.group(1).strip().replace("\n", " ") if reg_match else "Unknown Reg"

        # AADHAAR
        aadhaar_match = re.search(r"(?:Aadhaar|UID|ID)[:\s\n]+(\d{4}\s?\d{4}\s?\d{4})", text, re.I)
        aadhaar_val = aadhaar_match.group(1).strip() if aadhaar_match else "Not Found"

        return DeathCertificateData(
            deceased_name=clean_name.title(),
            date_of_death=dod_match.group(1) if dod_match else "Unknown Date",
            registration_number=reg_val,
            aadhaar_number=aadhaar_val,
            raw_text=text
        )

class EmailAssetScanner:
    def __init__(self):
        self.patterns = {
            "banking": (r"(HDFC|SBI|ICICI|AXIS|KOTAK|Standard Chartered)", "Bank"),
            "insurance": (r"(LIC|HDFC Life|Max Life|Tata AIA|ICICI Pru)", "Insurance"),
            "investment": (r"(EPFO|Zerodha|Groww|Upstox|Mutual Fund)", "Investment"),
            "tax": (r"([A-Z]{5}[0-9]{4}[A-Z]{1})", "Income Tax (PAN)")
        }

    def decode_gmail_body(self, payload: Dict) -> str:
        if 'parts' in payload:
            for part in payload['parts']:
                body = self.decode_gmail_body(part)
                if body: return body
        if payload.get('mimeType') == 'text/plain':
            data = payload.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        return ""

    def scan_text(self, text: str) -> List[Dict]:
        found = []
        for category, (regex, label) in self.patterns.items():
            match = re.search(regex, text, re.I)
            if match:
                institution_name = match.group(0).upper()
                found.append({
                    "type": category,
                    "institution": institution_name if category != "tax" else label,
                    "id": match.group(0) if category == "tax" else "Verified in Content"
                })
        return found

class SubscriptionManager:
    def __init__(self):
        self.services = {
            "Netflix": ["netflix"], "Spotify": ["spotify"], 
            "Amazon Prime": ["amazon", "prime"], "Gym Membership": ["gym", "fitness"],
            "Adobe": ["adobe", "creative cloud"]
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
            "banking": ["Original Death Certificate", "Claimant KYC", "Succession Certificate", "Bank Passbook"],
            "insurance": ["Original Policy Bond", "Certified Death Cert", "Discharge Form"],
            "investment": ["UAN Number", "Form 20", "Nominee ID"],
            "tax": ["PAN Card Copy", "Legal Heir Certificate"]
        }
    def get_docs(self, asset_type: str) -> List[str]:
        return self.registry.get(asset_type.lower(), ["Death Certificate", "Claimant ID Proof"])

class FormFiller:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir).resolve() if output_dir else Path(__file__).resolve().parent / "outputs"
        os.makedirs(self.output_dir, exist_ok=True)
    def generate_checklist(self, task_name: str, documents: List[str]) -> str:
        content = f"📋 BEREAVEMENT CHECKLIST: {task_name}\n" + "="*40 + "\n"
        content += "\n".join([f"[ ] {d}" for d in documents])
        file_path = self.output_dir / f"Checklist_{task_name.replace(' ', '_')}.txt"
        with open(file_path, "w", encoding="utf-8") as f: f.write(content)
        return str(file_path)

class LogisticsManager:
    def calculate_photocopy_needs(self, tasks: List) -> str:
        pending = [t for t in tasks if getattr(t, 'status', '') != "completed"]
        copies = len(pending) * 2
        return (f"📋 LOGISTICS SUMMARY\n--------------------------\n"
                f"Pending Tasks: {len(pending)}\nRecommended Copies: {copies}")