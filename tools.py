import re
import os
import logging
import pytesseract
import base64
from pathlib import Path
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from pydantic import BaseModel
from typing import Optional, List, Dict
from fpdf import FPDF

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ensure Tesseract uses an absolute path, configurable via environment
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH", r'C:/Program Files/Tesseract-OCR/tesseract.exe')

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
            logging.error(f"Error reading PDF: {e}")
            return ""

    def _extract_from_image(self, path: str) -> str:
        try:
            return pytesseract.image_to_string(Image.open(path))
        except Exception as e:
            logging.error(f"Error reading Image: {e}")
            return ""

    def _extract_structured_data(self, text: str) -> DeathCertificateData:
        name_pattern = r"(?:Name|Deceased Name)(?:\s+of\s+Deceased)?[:\s]+(.*?)(?=\s+(?:Date|Death|DOD|Reg|Place|Sex|Father|Mother|Aadhaar)|$)"
        name_match = re.search(name_pattern, text, re.I | re.DOTALL)
        raw_name = name_match.group(1).strip() if name_match else "Unknown Deceased"
        clean_name = re.sub(r"^(of\s+deceased|deceased|:)\s+", "", raw_name, flags=re.I).strip()

        dod_match = re.search(r"(?:Date|Death|DOD)[:\s\n]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text, re.I)
        reg_match = re.search(r"(?:Registration|Reg|Certificate)\s*No\.?[:\s\n]+([A-Z0-9\s/-]+)", text, re.I)
        reg_val = reg_match.group(1).strip().replace("\n", " ") if reg_match else "Unknown Reg"

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
            "banking": (r"(HDFC|SBI|ICICI|AXIS|KOTAK|Standard Chartered|Loan)", "Bank"),
            "insurance": (r"(LIC|HDFC Life|Max Life|Tata AIA|ICICI Pru)", "Insurance"),
            "investment": (r"(EPFO|Zerodha|Groww|Upstox|Mutual Fund|SIP)", "Investment"),
            "tax": (r"([A-Z]{5}[0-9]{4}[A-Z]{1})", "Income Tax (PAN)"),
            "utilities": (r"(Airtel|BESCOM|BSES|Jio|Vi)", "Utility") 
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
            "banking": ["Form 15H", "Annexure A (Claim Form)", "Death Certificate", "Succession Cert"],
            "insurance": ["Form 3783", "Original Policy", "NEFT Mandate"],
            "investment": ["EPF Form 20", "Form 10D", "Nominee ID"],
            "tax": ["ITR-V", "Legal Heir Certificate"],
            "utilities": ["Death Certificate", "Current Utility Bill", "Identity Proof of Legal Heir"],
            "municipal": ["Death Certificate", "Property Tax Receipt", "Legal Heir Certificate"]
        }
    def get_docs(self, asset_type: str) -> List[str]:
        return self.registry.get(asset_type.lower(), ["Death Certificate", "Claimant ID Proof"])

class FormFiller:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir).resolve() if output_dir else Path(__file__).resolve().parent / "outputs"
        os.makedirs(self.output_dir, exist_ok=True)

    def prepare_fill_data(self, identity: DeathCertificateData, task_title: str):
        return {
            "Form Name": f"Claim Request: {task_title}",
            "Field_1 (Deceased Name)": identity.deceased_name,
            "Field_2 (Date of Death)": identity.date_of_death,
            "Field_3 (ID Reference)": identity.aadhaar_number,
            "Field_4 (Reg No)": identity.registration_number,
            "Timestamp": "2026-04-09",
            "Status": "READY_FOR_SUBMISSION"
        }

    def prepare_letter_data(self, identity: DeathCertificateData, task_title: str):
        """
        Generates a formal request letter for utility transfers.
        """
        return {
            "Document Type": "Formal Request Letter",
            "Recipient": "The Station Manager / Relationship Manager",
            "Subject": f"Transfer of ownership for {task_title}",
            "Reference": f"Deceased: {identity.deceased_name} (Reg No: {identity.registration_number})",
            "Body": (f"I am writing to formally request the transfer of the account/connection associated with "
                     f"{identity.deceased_name}, who passed away on {identity.date_of_death}. "
                     f"I have attached the necessary Death Certificate for your verification. "
                     f"Please guide me on the subsequent steps to move this connection to my name."),
            "Attachments": "1. Death Certificate (Attested Copy), 2. Identity Proof of Claimant, 3. Last Paid Bill"
        }

    def generate_filled_pdf(self, form_data: Dict):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, txt=form_data["Form Name"], ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("helvetica", "", 12)
        for key, value in form_data.items():
            if key != "Form Name":
                pdf.set_font("helvetica", "B", 10)
                pdf.cell(0, 10, txt=f"{key}:", ln=True)
                pdf.set_font("helvetica", "", 12)
                pdf.cell(0, 10, txt=str(value), ln=True)
                pdf.ln(2)
        
        safe_form_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', form_data['Form Name'])
        file_name = f"Filled_{safe_form_name}.pdf"
        file_path = Path("static/downloads") / file_name
        pdf.output(str(file_path))
        return f"/static/downloads/{file_name}"

class PDFGenerator:
    def __init__(self, output_dir="static/downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_checklist_pdf(self, deceased_name, tasks):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, f"Bereavement Action Plan: {deceased_name}", ln=True, align="C")
        pdf.ln(10)
        
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(100, 10, "Task Description", 1, 0, "C")
        pdf.cell(90, 10, "Required Documents", 1, 1, "C")
        
        pdf.set_font("helvetica", "", 10)
        for task in tasks:
            title = getattr(task, 'title', task.get('title', 'N/A') if isinstance(task, dict) else 'N/A')
            docs = getattr(task, 'required_docs', task.get('required_docs', []) if isinstance(task, dict) else [])
            
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(100, 10, title, border=1)
            pdf.set_xy(x + 100, y)
            docs_text = ", ".join(docs) if docs else "N/A"
            pdf.multi_cell(90, 10, docs_text, border=1)
            
        file_name = f"Checklist_{deceased_name.replace(' ', '_')}.pdf"
        file_path = self.output_dir / file_name
        pdf.output(str(file_path))
        return f"/static/downloads/{file_name}"