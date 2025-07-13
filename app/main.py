import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from contextlib import asynccontextmanager

# Importer la logique depuis le fichier analysis_logic.py
from  .analysis_logic import load_bi_encoder,load_corpus_dataframe, load_cross_encoder, load_faiss_index, analyze_pdf_for_plagiarism

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

app = FastAPI(title="API de Détection de Plagiat", version="1.0", lifespan=lifespan)

@app.get("/", tags=["Status"])
def read_root():
    """Point d'entrée pour vérifier que l'API est en ligne."""
    return {"status": "ok", "message": "Bienvenue sur l'API de détection de plagiat."}

@app.post("/analyze-document/", tags=["Analyse"])
async def analyze_document(file: UploadFile = File(..., description="Le fichier PDF à analyser.")):
    """
    Analyse un document PDF pour détecter le plagiat.
    - Accepte un fichier PDF.
    - Retourne un rapport de similarité au format JSON.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Type de fichier invalide. Veuillez envoyer un PDF.")

    temp_dir = "temp_files"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}.pdf")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"Lancement de l'analyse pour le fichier : {file.filename}")
        results = analyze_pdf_for_plagiarism(
            file_path=file_path,
            bi_encoder=models['bi_encoder'],
            cross_encoder=models['cross_encoder'],
            index=models['faiss_index'],
            df_corpus=models['df_corpus']
        )
        print("Analyse terminée.")
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Une erreur interne est survenue : {str(e)}")
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        await file.close()