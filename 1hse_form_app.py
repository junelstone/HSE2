import streamlit as st
from fpdf import FPDF
from datetime import datetime
import base64

class HSEReportPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'FICHE DE CONTRÔLE HSE', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_hse_pdf(data):
    pdf = HSEReportPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Header Information
    pdf.cell(0, 10, f"Date de l'inspection : {data['date_inspection']}", 0, 1)
    pdf.cell(0, 10, f"Lieu / Site : {data['lieu_site']}", 0, 1)
    pdf.cell(0, 10, f"Installation : {data['installation']}", 0, 1)
    pdf.cell(0, 10, f"Inspecteur(s) : {data['inspecteurs']}", 0, 1)
    pdf.cell(0, 10, f"Département concerné : {data['departement']}", 0, 1)
    pdf.ln(10)
    
    # Inspection Sections
    sections = [
        ("1. CONTRÔLE GÉNÉRAL DE LA SÉCURITÉ", [
            "Port des EPI (casque, gants, lunettes, chaussures, etc.)",
            "Signalisation de sécurité visible et lisible",
            "Extincteurs accessibles et vérifiés",
            "Issues de secours dégagées",
            "Présence de plans d'évacuation"
        ]),
        ("2. PRÉVENTION DES RISQUES INCENDIE", [
            "Stockage sécurisé des produits inflammables",
            "Systèmes de détection incendie fonctionnels",
            "Exercices d'évacuation réalisés régulièrement"
        ]),
        ("3. CONTRÔLE DES ÉQUIPEMENTS", [
            "Vérification périodique des équipements sous pression",
            "Maintenance préventive à jour",
            "Absence de fuites (huile, gaz, etc.)"
        ]),
        ("4. ENVIRONNEMENT", [
            "Gestion des déchets (tri, stockage, élimination)",
            "Absence de pollution visible (sol, eau, air)",
            "Bruit dans les limites autorisées"
        ]),
        ("5. COMPORTEMENT DU PERSONNEL", [
            "Respect des consignes de sécurité",
            "Présence aux briefings sécurité",
            "Signalement des incidents / presqu'accidents"
        ]),
        ("6. FORMATION ET COMPÉTENCES", [
            "Formation HSE initiale pour tout nouveau personnel",
            "Formations périodiques (incendie, premiers secours, etc.) à jour",
            "Registre des formations disponible et à jour",
            "Évaluation des compétences après formation",
            "Sensibilisation aux procédures d'urgence"
        ])
    ]
    
    for section_title, items in sections:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, section_title, 0, 1)
        pdf.set_font('Arial', size=10)
        
        # Table Header
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(100, 8, "Éléments à vérifier", 1, 0, 'L', 1)
        pdf.cell(20, 8, "Conforme", 1, 0, 'C', 1)
        pdf.cell(25, 8, "Non conforme", 1, 0, 'C', 1)
        pdf.cell(0, 8, "Observations / Actions correctives", 1, 1, 'L', 1)
        
        for item in items:
            # Get the stored values for this item
            safe_key = f"{section_title}_{item}_conforme"
            unsafe_key = f"{section_title}_{item}_non_conforme"
            obs_key = f"{section_title}_{item}_observations"
            
            conform = "☑" if data.get(safe_key, False) else "☐"
            non_conform = "☑" if data.get(unsafe_key, False) else "☐"
            observations = data.get(obs_key, "")
            
            pdf.cell(100, 8, item, 1)
            pdf.cell(20, 8, conform, 1, 0, 'C')
            pdf.cell(25, 8, non_conform, 1, 0, 'C')
            pdf.multi_cell(0, 8, observations, 1)
        
        pdf.ln(5)
    
    # General Comments and Signatures
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Commentaires généraux :", 0, 1)
    pdf.set_font('Arial', size=10)
    pdf.multi_cell(0, 8, data['commentaires'])
    pdf.ln(15)
    
    # Signatures
    pdf.cell(90, 10, "Signature de l'inspecteur : _________________________", 0, 0)
    pdf.cell(0, 10, "Signature du responsable de site : _________________________", 0, 1)
    
    return pdf.output(dest='S').encode('latin1')

def main():
    st.set_page_config(page_title="HSE Inspection App", layout="wide")
    st.title("FICHE DE CONTRÔLE HSE")
    
    with st.form("hse_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            date_inspection = st.date_input("Date de l'inspection", datetime.now())
            lieu_site = st.text_input("Lieu / Site")
            installation = st.text_input("Installation")
            inspecteurs = st.text_input("Inspecteur(s)")
            
        with col2:
            departement = st.text_input("Département concerné")
            commentaires = st.text_area("Commentaires généraux")
        
        st.subheader("1. CONTRÔLE GÉNÉRAL DE LA SÉCURITÉ")
        general_safety_items = [
            "Port des EPI (casque, gants, lunettes, chaussures, etc.)",
            "Signalisation de sécurité visible et lisible",
            "Extincteurs accessibles et vérifiés",
            "Issues de secours dégagées",
            "Présence de plans d'évacuation"
        ]
        display_inspection_items("1. CONTRÔLE GÉNÉRAL DE LA SÉCURITÉ", general_safety_items)
        
        st.subheader("2. PRÉVENTION DES RISQUES INCENDIE")
        fire_items = [
            "Stockage sécurisé des produits inflammables",
            "Systèmes de détection incendie fonctionnels",
            "Exercices d'évacuation réalisés régulièrement"
        ]
        display_inspection_items("2. PRÉVENTION DES RISQUES INCENDIE", fire_items)
        
        st.subheader("3. CONTRÔLE DES ÉQUIPEMENTS")
        equipment_items = [
            "Vérification périodique des équipements sous pression",
            "Maintenance préventive à jour",
            "Absence de fuites (huile, gaz, etc.)"
        ]
        display_inspection_items("3. CONTRÔLE DES ÉQUIPEMENTS", equipment_items)
        
        st.subheader("4. ENVIRONNEMENT")
        environment_items = [
            "Gestion des déchets (tri, stockage, élimination)",
            "Absence de pollution visible (sol, eau, air)",
            "Bruit dans les limites autorisées"
        ]
        display_inspection_items("4. ENVIRONNEMENT", environment_items)
        
        st.subheader("5. COMPORTEMENT DU PERSONNEL")
        behavior_items = [
            "Respect des consignes de sécurité",
            "Présence aux briefings sécurité",
            "Signalement des incidents / presqu'accidents"
        ]
        display_inspection_items("5. COMPORTEMENT DU PERSONNEL", behavior_items)
        
        st.subheader("6. FORMATION ET COMPÉTENCES")
        training_items = [
            "Formation HSE initiale pour tout nouveau personnel",
            "Formations périodiques (incendie, premiers secours, etc.) à jour",
            "Registre des formations disponible et à jour",
            "Évaluation des compétences après formation",
            "Sensibilisation aux procédures d'urgence"
        ]
        display_inspection_items("6. FORMATION ET COMPÉTENCES", training_items)
        
        submitted = st.form_submit_button("Générer le rapport PDF")
        
        if submitted:
            data = {
                'date_inspection': date_inspection.strftime('%d/%m/%Y'),
                'lieu_site': lieu_site,
                'installation': installation,
                'inspecteurs': inspecteurs,
                'departement': departement,
                'commentaires': commentaires
            }
            
            # Collect all inspection items from session state
            for key, value in st.session_state.items():
                if key.startswith(('1.', '2.', '3.', '4.', '5.', '6.')):
                    data[key] = value
            
            pdf_bytes = create_hse_pdf(data)
            
            st.success("Rapport HSE généré avec succès!")
            
            # Display download button
            st.download_button(
                label="Télécharger le rapport PDF",
                data=pdf_bytes,
                file_name=f"hse_rapport_{date_inspection.strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

def display_inspection_items(section_title, items):
    for item in items:
        st.markdown(f"**{item}**")
        col1, col2, col3 = st.columns([1, 1, 3])
        
        with col1:
            safe_key = f"{section_title}_{item}_conforme"
            st.checkbox("Conforme", key=safe_key, value=False)
        
        with col2:
            unsafe_key = f"{section_title}_{item}_non_conforme"
            st.checkbox("Non conforme", key=unsafe_key, value=False)
        
        with col3:
            obs_key = f"{section_title}_{item}_observations"
            st.text_input("Observations / Actions correctives", key=obs_key)

if __name__ == '__main__':
    main()
