from flask import Flask, render_template_string, request, send_file
from fpdf import FPDF
import io

app = Flask(__name__)

form_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Fiche de Contrôle HSE</title>
</head>
<body>
    <h2>Fiche de Contrôle HSE</h2>
    <form action="/generate_pdf" method="post">
        <label>Date de l'inspection:</label><br>
        <input type="date" name="date_inspection"><br><br>
        
        <label>Lieu / Site:</label><br>
        <input type="text" name="lieu"><br><br>
        
        <label>Installation:</label><br>
        <input type="text" name="installation"><br><br>
        
        <label>Inspecteur(s):</label><br>
        <input type="text" name="inspecteurs"><br><br>
        
        <label>Département concerné:</label><br>
        <input type="text" name="departement"><br><br>
        
        <label>Commentaires généraux:</label><br>
        <textarea name="commentaires" rows="5" cols="40"></textarea><br><br>
        
        <label>Signature de l'inspecteur:</label><br>
        <input type="text" name="signature_inspecteur"><br><br>
        
        <label>Signature du responsable de site:</label><br>
        <input type="text" name="signature_responsable"><br><br>
        
        <input type="submit" value="Générer le PDF">
    </form>
</body>
</html>
"""

@app.route('/')
def form():
    return render_template_string(form_template)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    data = request.form

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    fields = [
        ("Date de l'inspection", data.get('date_inspection', '')),
        ("Lieu / Site", data.get('lieu', '')),
        ("Installation", data.get('installation', '')),
        ("Inspecteur(s)", data.get('inspecteurs', '')),
        ("Département concerné", data.get('departement', '')),
        ("Commentaires généraux", data.get('commentaires', '')),
        ("Signature de l'inspecteur", data.get('signature_inspecteur', '')),
        ("Signature du responsable de site", data.get('signature_responsable', '')),
    ]

    for label, value in fields:
        pdf.multi_cell(0, 10, f"{label}: {value}")

    pdf_output = io.BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)

    return send_file(pdf_output, as_attachment=True, download_name="fiche_HSE.pdf", mimetype='application/pdf')

if name == '__main__':
    app.run(debug=True)
