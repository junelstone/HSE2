from flask import Flask, render_template_string, request, send_file, Response
from fpdf import FPDF
import io
import base64

app = Flask(__name__)

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
        .button-group { display: flex; gap: 10px; margin-top: 20px; }
        input[type="submit"], button {
            flex: 1;
            padding: 12px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        #generate-pdf { background-color: #4CAF50; color: white; }
        #generate-pdf:hover { background-color: #45a049; }
        #preview-pdf { background-color: #2196F3; color: white; }
        #preview-pdf:hover { background-color: #0b7dda; }
        h2 { color: #333; text-align: center; }
        iframe { width: 100%; height: 500px; border: 1px solid #ddd; margin-top: 20px; }
    </style>
</head>
<body>
    <h2>Fiche de Contrôle HSE</h2>
    <form id="hse-form">
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
        
        <div class="button-group">
            <input type="submit" id="generate-pdf" value="Générer le PDF">
            <button type="button" id="preview-pdf">Aperçu PDF</button>
        </div>
    </form>
    
    <div id="pdf-preview-container" style="display: none;">
        <h3>Aperçu du PDF</h3>
        <iframe id="pdf-preview"></iframe>
    </div>

    <script>
        document.getElementById('preview-pdf').addEventListener('click', async function() {
            const form = document.getElementById('hse-form');
            const formData = new FormData(form);
            
            try {
                const response = await fetch('/preview_pdf', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    
                    document.getElementById('pdf-preview').src = url;
                    document.getElementById('pdf-preview-container').style.display = 'block';
                } else {
                    alert('Erreur lors de la génération de l\'aperçu');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Une erreur est survenue');
            }
        });

        document.getElementById('hse-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            try {
                const response = await fetch('/generate_pdf', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    
                    // Create temporary link to trigger download
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'fiche_controle_HSE.pdf';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                } else {
                    alert('Erreur lors de la génération du PDF');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Une erreur est survenue');
            }
        });
    </script>
</body>
</html>
"""

def generate_pdf_content(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Fiche de Contrôle HSE", 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)

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

    return pdf.output(dest='S').encode('latin1')

@app.route('/')
def show_form():
    return render_template_string(form_template)

@app.route('/preview_pdf', methods=['POST'])
def preview_pdf():
    try:
        pdf_content = generate_pdf_content(request.form)
        return Response(
            pdf_content,
            mimetype='application/pdf',
            headers={'Content-Disposition': 'inline; filename=preview.pdf'}
        )
    except Exception as e:
        return f"Une erreur est survenue: {str(e)}", 500

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    try:
        pdf_content = generate_pdf_content(request.form)
        return Response(
            pdf_content,
            mimetype='application/pdf',
            headers={'Content-Disposition': 'attachment; filename=fiche_controle_HSE.pdf'}
        )
    except Exception as e:
        return f"Une erreur est survenue: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
