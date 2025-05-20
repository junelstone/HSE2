# First install required packages if you haven't:
# pip install flask fpdf

from flask import Flask, render_template_string, request, Response
from fpdf import FPDF
import io

app = Flask(__name__)

# HTML template remains the same as in previous working version
form_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Fiche de Contrôle HSE</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        form { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        label { display: block; margin-top: 15px; font-weight: bold; }
        input[type="text"], input[type="date"], textarea {
            width: 100%;
            padding: 8px;
            margin-top: 5px;
            box-sizing: border-box;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        textarea { height: 100px; resize: vertical; }
        input[type="submit"] {
            background-color: #4CAF50;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 20px;
            font-size: 16px;
        }
        input[type="submit"]:hover { background-color: #45a049; }
        h2 { color: #333; text-align: center; }
    </style>
</head>
<body>
    <h2>Fiche de Contrôle HSE</h2>
    <form action="/generate_pdf" method="post">
        <label for="date_inspection">Date de l'inspection:</label>
        <input type="date" id="date_inspection" name="date_inspection" required>
        
        <label for="lieu">Lieu / Site:</label>
        <input type="text" id="lieu" name="lieu" required>
        
        <label for="installation">Installation:</label>
        <input type="text" id="installation" name="installation" required>
        
        <label for="inspecteurs">Inspecteur(s):</label>
        <input type="text" id="inspecteurs" name="inspecteurs" required>
        
        <label for="departement">Département concerné:</label>
        <input type="text" id="departement" name="departement" required>
        
        <label for="commentaires">Commentaires généraux:</label>
        <textarea id="commentaires" name="commentaires" required></textarea>
        
        <label for="signature_inspecteur">Signature de l'inspecteur:</label>
        <input type="text" id="signature_inspecteur" name="signature_inspecteur" required>
        
        <label for="signature_responsable">Signature du responsable de site:</label>
        <input type="text" id="signature_responsable" name="signature_responsable" required>
        
        <input type="submit" value="Générer le PDF">
    </form>
</body>
</html>
"""

@app.route('/')
def show_form():
    return render_template_string(form_template)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.form

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Add title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Fiche de Contrôle HSE", 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font("Arial", size=12)

        # Add form data
        fields = [
            ("Date de l'inspection", data.get('date_inspection', 'N/A')),
            ("Lieu/Site", data.get('lieu', 'N/A')),
            ("Installation", data.get('installation', 'N/A')),
            ("Inspecteur(s)", data.get('inspecteurs', 'N/A')),
            ("Département concerné", data.get('departement', 'N/A')),
            ("Commentaires généraux", data.get('commentaires', 'Aucun commentaire')),
            ("Signature de l'inspecteur", data.get('signature_inspecteur', 'Non fournie')),
            ("Signature du responsable", data.get('signature_responsable', 'Non fournie')),
        ]

        for label, value in fields:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(40, 10, label + ":", 0, 0)
            pdf.set_font("Arial", '', 12)
            pdf.multi_cell(0, 10, value)
            pdf.ln(5)

        # Generate PDF in memory
        pdf_output = io.BytesIO()
        pdf_output.write(pdf.output(dest='S').encode('latin1'))
        pdf_output.seek(0)

        return Response(
            pdf_output.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': 'attachment; filename=fiche_controle_HSE.pdf'}
        )

    except Exception as e:
        return f"Une erreur est survenue: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
