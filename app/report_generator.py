import os
from datetime import datetime
from xhtml2pdf import pisa
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))

def create_html_report(analysis_data: dict, document_name: str) -> str:
    """
    Génère le contenu HTML complet du rapport à partir des données d'analyse.
    """
    template = env.from_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rapport d'Analyse de Plagiat</title>
        <style>
            @page {
                size: a4 portrait;
                @frame header_frame { -pdf-frame-content: header_content; left: 50pt; width: 512pt; top: 50pt; height: 40pt; }
                @frame content_frame { left: 50pt; width: 512pt; top: 90pt; height: 632pt; }
                @frame footer_frame { -pdf-frame-content: footer_content; left: 50pt; width: 512pt; top: 722pt; height: 20pt; }
            }
            body { font-family: 'Helvetica', 'Arial', sans-serif; color: #333; }
            h1 { text-align: center; color: #4a4a4a; }
            h2 { border-bottom: 2px solid #eee; padding-bottom: 5px; color: #4a4a4a; }
            .summary { background-color: #f9f9f9; border: 1px solid #eee; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .finding { border: 1px solid #ddd; padding: 10px; margin-bottom: 15px; border-radius: 5px; page-break-inside: avoid; }
            .verdict { font-weight: bold; }
            .verdict.high { color: #d9534f; }
            .verdict.medium { color: #f0ad4e; }
            .details { font-size: 0.8em; color: #777; }
            .diff { font-family: monospace; padding: 10px; border-left: 3px solid #ccc; margin-top: 10px; background-color: #fafafa; }
            #header_content { text-align: right; font-size: 0.8em; color: #888; }
            #footer_content { text-align: center; font-size: 0.8em; color: #888; }
        </style>
    </head>
    <body>
        <div id="header_content">
            Rapport généré le {{ generation_date }}
        </div>
        <div id="footer_content">
            Page <pdf:pagecount> de <pdf:pagecount>
        </div>

        <h1>Rapport d'Analyse de Plagiat</h1>
        
        <h2>Synthèse pour le document : {{ document_name }}</h2>
        <div class="summary">
            - <b>Phrases analysées :</b> {{ summary.phrases_analysees }} <br>
            - <b>Phrases suspectes détectées :</b> {{ summary.phrases_suspectes }} <br>
            - <b>Taux de suspicion global :</b> {{ summary.ratio_suspicion }}
        </div>

        <h2>Détail des similarités trouvées</h2>
        {% if findings %}
            {% for finding in findings %}
                <div class="finding">
                    <p>
                        <span class="verdict {{ 'high' if 'Copié-collé' in finding.verdict else 'medium' }}">
                            Verdict : {{ finding.verdict }}
                        </span> 
                        (Score Composite : {{ finding.score_composite }})
                    </p>
                    <p class="details">Source identifiée : <i>{{ finding.document_source }}</i></p>
                    
                    <p><b>Phrase du document :</b></p>
                    <div class="diff" style="border-left-color: #d9534f;">{{ finding.html_diff_suspecte | safe }}</div>
                    
                    <p><b>Source la plus proche :</b></p>
                    <div class="diff" style="border-left-color: #5cb85c;">{{ finding.html_diff_source | safe }}</div>
                </div>
            {% endfor %}
        {% else %}
            <p>✅ Aucune similarité suspecte n'a été trouvée dans le document.</p>
        {% endif %}
    </body>
    </html>
    """)
    html_content = template.render(
        summary=analysis_data['summary'],
        findings=analysis_data['findings'],
        document_name=document_name,
        generation_date=datetime.now().strftime("%d/%m/%Y à %H:%M")
    )
    return html_content

def generate_pdf_report(analysis_data: dict, document_name: str) -> str:
    """
    Génère un rapport PDF à partir des données d'analyse et le sauvegarde temporairement.
    Retourne le chemin du fichier PDF créé.
    """
    html_string = create_html_report(analysis_data, document_name)
    
    # Créer un dossier temporaire pour les rapports
    temp_dir = "temp_reports"
    os.makedirs(temp_dir, exist_ok=True)
    report_path = os.path.join(temp_dir, f"rapport_{document_name}.pdf")

    with open(report_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)

    if pisa_status.err:
        raise Exception("Erreur lors de la génération du PDF.")
        
    return report_path