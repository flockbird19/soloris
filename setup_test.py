from fpdf import FPDF
import os

def create_mock_data():
    os.makedirs("data/uploads", exist_ok=True)

    # 1. Create Mock Death Certificate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "GOVERNMENT OF MAHARASHTRA", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, "DEPARTMENT OF HEALTH", ln=True, align='C')
    pdf.ln(10)
    
    # These fields must match your regex in tools.py
    pdf.cell(200, 10, "Name of Deceased: Kabir Mehra", ln=True)
    pdf.cell(200, 10, "Date of Death: 15/03/2026", ln=True)
    pdf.cell(200, 10, "Registration No: MH/2026/045891", ln=True)
    pdf.cell(200, 10, "Place of Death: Mumbai, Maharashtra", ln=True)
    
    pdf.output("data/uploads/death_certificate.pdf")
    print("✅ Generated: data/uploads/death_certificate.pdf")

    # 2. Create Mock Email Text File
    email_content = """
    From: notifications@hdfcbank.com
    Subject: Your HDFC Bank Account 99887700 statement
    Body: Dear Customer, your monthly statement for Account No: 99887700 is ready.
    
    From: service@licindia.com
    Subject: LIC Premium Receipt - Policy 123456789
    Body: Thank you for paying the premium for Policy Number: 123456789.
    """
    with open("data/uploads/mock_email.txt", "w", encoding="utf-8") as f:
        f.write(email_content)
    print("✅ Generated: data/uploads/mock_email.txt")

if __name__ == "__main__":
    create_mock_data()