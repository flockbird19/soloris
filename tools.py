import re
import os
import json
import logging
import anthropic
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
        api_key = os.getenv("CLAUDE_KEY")
        if not api_key:
            logging.error("Missing API Key for Identity Parser")
            return DeathCertificateData(deceased_name="Unknown", date_of_death="Unknown", registration_number="Unknown", raw_text=text)

        client = anthropic.Anthropic(api_key=api_key)
        system_prompt = """
        You are a document data extractor. Given the raw OCR text of a Death Certificate, extract the following fields strictly as a JSON object:
        - "deceased_name" (Full name of the deceased, title cased)
        - "date_of_death" (Date of death)
        - "registration_number" (The official registration or certificate number)
        - "aadhaar_number" (The 12-digit Aadhaar/UID if present, otherwise "Not Found")
        
        Return ONLY valid JSON. Do not include markdown formatting or extra text.
        """
        
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                system=system_prompt,
                messages=[{"role": "user", "content": text}]
            )
            response_text = message.content[0].text.strip()
            if response_text.startswith("```json"): response_text = response_text[7:-3]
            elif response_text.startswith("```"): response_text = response_text[3:-3]
            
            data = json.loads(response_text)
            return DeathCertificateData(
                deceased_name=data.get("deceased_name", "Unknown"),
                date_of_death=data.get("date_of_death", "Unknown"),
                registration_number=data.get("registration_number", "Unknown"),
                aadhaar_number=data.get("aadhaar_number", "Not Found"),
                raw_text=text
            )
        except Exception as e:
            logging.error(f"LLM Identity Parsing failed: {e}")
            return DeathCertificateData(deceased_name="Unknown", date_of_death="Unknown", registration_number="Unknown", raw_text=text)

class LLMAssetScanner:
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

    def extract_assets(self, email_snippets: List[str]) -> List[Dict]:
        api_key = os.getenv("CLAUDE_KEY")
        if not api_key or not email_snippets:
            return []

        client = anthropic.Anthropic(api_key=api_key)
        
        system_prompt = """
        You are a financial asset extractor. Extract actual financial assets (bank accounts, insurance policies, investments) and digital subscriptions (like Netflix, Spotify, Amazon Prime, etc.) from the provided email snippets. 
        Ignore promotional emails or general newsletters. 
        Return ONLY a strict JSON array of objects with keys:
        - "type" (one of: banking, insurance, investment, tax, utilities, subscription)
        - "institution" (e.g. HDFC Bank, LIC, Netflix, Spotify)
        - "id" (the account number, last 4 digits, or policy number if found, else "Unknown")
        If no assets or subscriptions are found, return []. Do not include markdown formatting or any other text.
        """
        
        combined_text = "\n\n---EMAIL---\n\n".join(email_snippets)
        
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": combined_text}]
            )
            response_text = message.content[0].text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
                
            return json.loads(response_text)
        except Exception as e:
            logging.error(f"LLM Extraction failed: {e}")
            return []

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
        pdf.cell(0, 10, txt="UNIVERSAL BEREAVEMENT CLAIM FORM", ln=True, align='C')
        pdf.set_font("helvetica", "I", 10)
        pdf.cell(0, 10, txt=form_data.get("Form Name", "Claim Request"), ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("helvetica", "", 12)
        for key, value in form_data.items():
            if key != "Form Name":
                pdf.set_font("helvetica", "B", 10)
                pdf.cell(60, 10, txt=f"{key}:", border=1)
                pdf.set_font("helvetica", "", 10)
                pdf.cell(0, 10, txt=str(value), border=1, ln=True)
                pdf.ln(2)
        
        pdf.ln(20)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(90, 10, txt="Claimant Signature: _______________________", ln=False)
        pdf.cell(0, 10, txt="Date: _______________________", ln=True)
        
        # Legal Disclaimer Footer
        pdf.set_y(-30)
        pdf.set_font("helvetica", "I", 8)
        pdf.multi_cell(0, 5, txt="Disclaimer: This is a guidance tool and auto-generated claim form. It does not constitute legal advice. Please verify all information and consult the respective institution before submission.", align="C")
        
        safe_form_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', form_data.get('Form Name', 'Form'))
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
            
        # Legal Disclaimer Footer
        pdf.set_y(-30)
        pdf.set_font("helvetica", "I", 8)
        pdf.multi_cell(0, 5, txt="Disclaimer: This is a guidance tool. It does not constitute legal advice. Please verify all requirements with the respective institution.", align="C")
            
        file_name = f"Checklist_{deceased_name.replace(' ', '_')}.pdf"
        file_path = self.output_dir / file_name
        pdf.output(str(file_path))
        return f"/static/downloads/{file_name}"