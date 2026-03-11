from fpdf import FPDF

def generate(data):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", size=12)

    for k,v in data.items():
        pdf.cell(200,10,txt=f"{k}:{v}", ln=True)

    pdf.output("report.pdf")
