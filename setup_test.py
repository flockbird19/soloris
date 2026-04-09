from fpdf import FPDF
import os
import random

def create_mock_data():
    os.makedirs("data/uploads", exist_ok=True)

    pdf = FPDF()
    pdf.add_page()

    # Random font size variations
    pdf.set_font("Arial", 'B', random.choice([14, 16, 18]))
    pdf.cell(200, 10, "Govt. of Maharashtra", ln=True, align='C')

    pdf.set_font("Arial", '', random.choice([10, 12]))
    pdf.cell(200, 8, "Department   of   Health Services", ln=True, align='C')

    pdf.ln(8)

    # Add noise text
    pdf.set_font("Arial", '', 9)
    pdf.multi_cell(0, 6, "This certificate is digitally generated and may contain irregular formatting. Ref Code: XJ29-KL2P")

    pdf.ln(5)

    pdf.set_font("Arial", '', 12)

    # Intentionally messy formatting
    pdf.multi_cell(0, 8, "Name of Deceased :   Aarav   Sharma")
    pdf.multi_cell(0, 8, "Aadhaar No :  1234 5678 9123")
    
    pdf.multi_cell(0, 8, "Date of\nDeath :  21 / 02 / 2026")

    pdf.multi_cell(0, 8, "Registration No:\n MH - 2026 - 998172")

    pdf.multi_cell(0, 8, "Place of Death :\n Pune , Maharashtra")

    pdf.ln(10)

    # Add random footer noise
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, "Note: This document may include OCR inconsistencies.\nAuthorized Signatory\n( Digitally Signed )")

    pdf.output("data/uploads/death_certificate_hard.pdf")
    print("✅ Generated: data/uploads/death_certificate_hard.pdf")

if __name__ == "__main__":
    create_mock_data()