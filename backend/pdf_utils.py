import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
from flask import current_app

def generate_enrollment_certificate(student, dest_folder):
    """
    Generates a PDF enrollment certificate for the cadet.
    Returns the filename of the generated PDF.
    """
    os.makedirs(dest_folder, exist_ok=True)
    filename = f"enrollment_cert_{student.roll_no}_{student.id}.pdf"
    file_path = os.path.join(dest_folder, filename)

    c = canvas.Canvas(file_path, pagesize=landscape(letter))
    width, height = landscape(letter)

    # Background Block
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(0, 0, width, height, fill=1)
    
    # Border
    c.setStrokeColorRGB(0.1, 0.1, 0.4)
    c.setLineWidth(4)
    c.rect(0.5*inch, 0.5*inch, width-1*inch, height-1*inch)

    c.setStrokeColorRGB(0.8, 0.6, 0.1)
    c.setLineWidth(2)
    c.rect(0.6*inch, 0.6*inch, width-1.2*inch, height-1.2*inch)

    # Title
    c.setFillColor(colors.darkblue)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width/2.0, height - 2*inch, "NATIONAL CADET CORPS")
    
    c.setFont("Helvetica", 18)
    c.drawCentredString(width/2.0, height - 2.5*inch, "Govt. Polytechnic Hamirpur (HP)")

    # Certificate Type Let
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2.0, height - 3.5*inch, "ENROLLMENT CERTIFICATE")

    # Body
    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2.0, height - 4.5*inch, "This is to certify that")

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2.0, height - 5.0*inch, f"Cadet {student.first_name.upper()} {student.last_name.upper()}")

    c.setFont("Helvetica", 14)
    text = f"Roll No: {student.roll_no} | Branch: {student.branch} | Year: {student.year}"
    c.drawCentredString(width/2.0, height - 5.5*inch, text)
    
    status_text = f"has been officially {student.status.upper()} in the {student.ncc_wing} Wing."
    c.drawCentredString(width/2.0, height - 6.0*inch, status_text)
    
    if student.cadet_no:
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width/2.0, height - 6.5*inch, f"Assigned Cadet No: {student.cadet_no}")

    # Signatures
    c.setFont("Helvetica", 12)
    c.drawString(1.5*inch, 1.5*inch, "Date: " + datetime.utcnow().strftime("%Y-%m-%d"))
    c.line(1.5*inch, 1.4*inch, 3.5*inch, 1.4*inch)
    
    c.drawString(width - 4*inch, 1.5*inch, "Signature of ANO / Officer")
    c.line(width - 4*inch, 1.4*inch, width - 1.5*inch, 1.4*inch)

    c.showPage()
    c.save()
    
    return filename
