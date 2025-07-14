import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse

# Importer la logique depuis le fichier analysis_logic.py
from  .analysis_logic import load_bi_encoder,load_corpus_dataframe, load_cross_encoder, load_faiss_index, analyze_pdf_for_plagiarism
from .report_generator import create_html_report, generate_pdf_report
# Dictionnaire pour garder les modèles en mémoire pendant que l'API tourne
models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Fonction pour charger les modèles au démarrage de l'API 
    et les garder disponibles durant toute sa vie.
    """
    print("Chargement des ressources (modèles, index, corpus)...")
    models['bi_encoder'] = load_bi_encoder()
    models['cross_encoder'] = load_cross_encoder()
    models['faiss_index'] = load_faiss_index()
    models['df_corpus'] = load_corpus_dataframe()
    print("✅ Ressources chargées avec succès.")
    yield
    # Code à exécuter à l'arrêt de l'application (libérer la mémoire)
    models.clear()
    print("Ressources libérées.")

app = FastAPI(title="A-Plag API", version="1.0", lifespan=lifespan)

@app.get("/", tags=["Status"])
def read_root():
    """Point d'entrée pour vérifier que l'API est en ligne."""
    return {"status": "ok", "message": "Bienvenue sur l'API de A-PLAG"}

@app.post("/generate-report", tags=["Analyse"])
async def generate_plagiarism_report(file: UploadFile=File(..., description="Le fichier PDF à analyser.")):
    """
    Analyse un PDF.
    - Retourne un fichier à télécharger

    """

    if file.content_type !="application/pdf":
        raise HTTPException(status_code=400, detail="Type de fichier invalide. Veuillez envoyer un PDF. ")
    temp_dir="temp_files"
    staging_dir="staging_files"
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    upload_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}.pdf")
    report_path = None # Pour stocker le chemin du rapport généré

    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # Étape 2: Obtenir les résultats de l'analyse (le JSON)
        print(f"Lancement de l'analyse pour : {file.filename}")
        analysis_results = analyze_pdf_for_plagiarism(
            file_path=upload_path,
            bi_encoder=models['bi_encoder'],
            cross_encoder=models['cross_encoder'],
            index=models['faiss_index'],
            df_corpus=models['df_corpus'],
            min_verdict_score=0.5
        )
        print("Analyse terminée. Génération du rapport PDF...")
        shutil.move(upload_path, os.path.join(staging_dir, file.filename))

        report_path = generate_pdf_report(
            analysis_data=analysis_results,
            document_name=file.filename
        )
        print(f"Rapport généré : {report_path}")

        # Étape 4: Renvoyer le fichier PDF
        # FileResponse s'occupe de lire le fichier et de le streamer.
        # Il gère aussi les en-têtes HTTP (Content-Type, Content-Disposition).
        return FileResponse(
            path=report_path,
            media_type='application/pdf',
            filename=f"Rapport_{file.filename}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Une erreur interne est survenue : {str(e)}")
        
    finally:
        # Étape 5: Nettoyage des fichiers temporaires
        if os.path.exists(upload_path):
            os.remove(upload_path)
        # Le rapport généré sera supprimé par le système d'exploitation plus tard
        # ou vous pouvez ajouter un mécanisme de nettoyage périodique.
        await file.close()

    


