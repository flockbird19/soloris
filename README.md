# Soloris - GriefOS

Soloris is a next-generation AI bereavement administration system designed to simplify the complex administrative burden placed on grieving families. It acts as an automated executor, intelligently scanning digital footprints and generating the required legal documentation to claim financial assets and close digital accounts.

## Core Features

- **100% LLM-Powered Identity Extraction**: Securely upload a Death Certificate to automatically extract critical identity details (Name, Date of Death, Registration Number) using Claude-3.5-Sonnet via Tesseract OCR pipelines.
- **Automated Digital Estate Discovery**: Securely connects to the deceased's Gmail account (via strict, consent-based API scopes) to scan the last 5 years of emails. It uses advanced LLM extraction to automatically map out a comprehensive "Financial Footprint" including:
  - Banking & Investments (e.g., HDFC, SBI, Zerodha)
  - Insurance Policies (e.g., LIC, Term Life)
  - Digital Subscriptions (e.g., Netflix, Spotify, Gym Memberships)
- **Trust-First Consent Flow**: The system enforces a mandatory "Dry Run" where it previews the number of financial emails discovered, requiring explicit user consent before any data is sent to the LLM for extraction.
- **Dynamic Task Engine**: Intelligently generates a customized "Bereavement Checklist" based on the assets discovered, including the specific legal documents required for each institution.
- **Automated Document Generation**: Instantly fills out complex legal claim forms and writes formal utility transfer letters, exporting them as ready-to-print PDFs.
- **Encrypted Session Persistence**: Offers the ability to safely export and import active sessions as encrypted JSON tokens to prevent data loss across sessions.

## Architecture & Security

- **Backend**: Python 3.11+ / FastAPI / Uvicorn
- **Frontend**: Jinja2 Templates with custom, premium minimal CSS (Vanilla)
- **AI Integration**: Anthropic Claude APIs
- **Document Processing**: PyPDF2, PDF2Image, Tesseract OCR, FPDF
- **Security Focus**: Complete reliance on isolated `SessionMiddleware` preventing cross-contamination, with zero database storage of PII to ensure absolute privacy for the grieving family.

## Setup Instructions

1. Install dependencies using `uv`:
   ```bash
   uv sync
   ```
2. Configure your environment variables in `.env`:
   ```env
   CLAUDE_KEY=your_anthropic_api_key
   TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe
   ```
3. Run the development server:
   ```bash
   uv run uvicorn main:app --reload
   ```
4. Access the Agent Console at `http://127.0.0.1:8000/`.
