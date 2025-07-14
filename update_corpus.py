import os
import shutil
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
import fitz
import nltk
import pandas as pd
import re
import os
import fitz  # Import de la bibliothèque PyMuPDF
from tqdm import tqdm

APP_DIR = "app"
CORPUS_DIR = os.path.join(APP_DIR, "corpus")
STAGING_DIR = "staging_files"
ARCHIVE_DIR = "archived_files"
CSV_FILES=os.path.join(CORPUS_DIR,"paragraphes-split.csv")
FAISS_INDEX_PATH = os.path.join(CORPUS_DIR, 'corpus_doc.index')
CORPUS_DF_PATH = os.path.join(CORPUS_DIR, 'corpus_dataframe_doc.pkl')
BI_ENCODER_NAME = 'sentence-transformers/msmarco-distilbert-base-v4'
TEXT_COLUMN = 'content_block'
SOURCE_COLUMN = 'title'
MIN_CHARS_PAR_BLOC = 300
MAX_CHARS_PAR_BLOC = 400
os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)





def extraire_texte_du_pdf(chemin_pdf):
    """Ouvre un fichier PDF et en extrait tout le contenu textuel."""
    try:
        document = fitz.open(chemin_pdf)
        texte_complet = ""
        for page in tqdm(document, desc="Extraction du texte du PDF"):
            texte_complet += page.get_text()
        return texte_complet
    except Exception as e:
        print(f"❌ ERREUR lors de la lecture du fichier PDF : {e}")
        return None

def nettoyer_texte(texte):
    """Nettoie le texte en retirant les éléments superflus."""
    texte = str(texte)
    texte = re.sub(r'\s+', ' ', texte).strip()
    texte = re.sub(r'\'', ' ', texte, flags=re.IGNORECASE)
    texte = re.sub(r'^\d+\s|\s\d+$', ' ', texte).strip()
    return texte

def contient_expression_math(texte):
    """Vérifie si un bloc de texte contient des expressions mathématiques."""
    texte = texte.lower()
    patterns = [
        r'[^a-zA-Z0-9\s](=|\+|-|\*|/)[^a-zA-Z0-9\s]',
        r'\bsqrt\b', r'\bsin\b', r'\bcos\b', r'\btan\b', r'\blog\b', r'\bln\b',
        r'\^', r'[∑√π∆µ∫≈≤≥≠≃≅]'
    ]
    for p in patterns:
        if re.search(p, texte):
            return True
    return False

def decouper_texte_en_blocs(texte, min_chars, max_chars):
    """Découpe un long texte en blocs de taille définie, en respectant les phrases."""
    phrases = re.split(r'(?<=[.!?])\s+', texte.strip())
    blocs = []
    bloc_actuel = ""

    for phrase in phrases:
        if len(bloc_actuel) + len(phrase) + 1 <= max_chars:
            bloc_actuel += phrase + " "
        else:
            if len(bloc_actuel.strip()) >= min_chars:
                blocs.append(bloc_actuel.strip())
            bloc_actuel = phrase + " "

    if bloc_actuel and min_chars <= len(bloc_actuel.strip()) <= max_chars:
        blocs.append(bloc_actuel.strip())

    return blocs


# --- PIPELINE PRINCIPAL ---

def traiter_et_ajouter_document(filename):
    """Fonction principale qui orchestre l'extraction, le traitement et l'ajout au CSV."""
    
    print(f"📄 1/4 - Extraction du texte depuis : {filename}")
    texte_complet = extraire_texte_du_pdf(filename)
    
    if not texte_complet:
        return

    print("ጽ 2/4 - Nettoyage et découpage du texte...")
    texte_nettoye = nettoyer_texte(texte_complet)
    blocs = decouper_texte_en_blocs(texte_nettoye, MIN_CHARS_PAR_BLOC, MAX_CHARS_PAR_BLOC)
    
    if not blocs:
        print("❌ AVERTISSEMENT : Aucun bloc de texte conforme n'a pu être généré.")
        return

    print(f"📊 3/4 - Préparation de {len(blocs)} blocs pour l'ajout...")
    donnees_a_ajouter = []
    for bloc in tqdm(blocs, desc="Filtrage des blocs"):
        if not contient_expression_math(bloc):
            donnees_a_ajouter.append({
                "title": filename,
                "content_block": bloc
                
            })

    df_nouveau = pd.DataFrame(donnees_a_ajouter)
    fichier_existe = os.path.exists(CSV_FILES)

    print(f"💾 4/4 - Ajout des données au fichier : {CSV_FILES}")
    df_nouveau.to_csv(
        CSV_FILES, 
        mode='a',
        index=False, 
        header=not fichier_existe
    )
    
    print("\n✅ Opération terminée avec succès !")
    print(f"Nombre total de paragraphes ajoutés : {len(df_nouveau)}")

def update_corpus():
    os.makedirs(STAGING_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    files_to_process=[f for f in os.listdir(STAGING_DIR) if f.endswith(".pdf") ]

    if not files_to_process:
        print("Aucun nouveau document à traiter")
        return
    
    try:
        df_corpus=pd.read_pickle(CORPUS_DF_PATH)
        index=faiss.read_index(FAISS_INDEX_PATH)
        bi_encoder=SentenceTransformer(BI_ENCODER_NAME)

    except FileNotFoundError:
        return
    
    new_paragraphs=[]

    for filename in files_to_process:
        file_path=os.path.join(STAGING_DIR, filename)

        if os.path.getsize(file_path)<10000:
            print(f"fichier trop petit. Ignoré")
            shutil.move(file_path, os.path.join(ARCHIVE_DIR, filename))
            continue

        try:
            doc=fitz.open(file_path)
            full_text="".join(page.get_text() for page in doc).replace('\n', ' ')
            doc.close()

            sentences=nltk.sent_tokenize(full_text, language='french')

            for sentence in sentences:
                if len(sentence.split()>10):
                    new_paragraphs.append({
                        TEXT_COLUMN:sentence,
                        SOURCE_COLUMN:filename
                    })

            shutil.move(file_path, os.path.join(ARCHIVE_DIR, filename))

        except Exception as e:
            print(f"Erreur lors du traitement du fichier{filename} : {e}")
            error_dir=os.path.join(STAGING_DIR, "errors")
            os.makedirs(error_dir, exist_ok=True)
            shutil.move(file_path, os.path.join(error_dir, filename))

    if not new_paragraphs:
        print("Aucun Paragraphe valide à ajouter")
        return
    
    print('\nMise à jour du Dataframe et de FAISS')

    df_new=pd.DataFrame(new_paragraphs)
    df_updated=pd.concat([df_corpus, df_new], ignore_index=True)
    df_updated.drop_duplicates(subset=[TEXT_COLUMN], inplace=True, keep='first')

    new_embeddings = bi_encoder.encode(
        df_new[TEXT_COLUMN].tolist(), 
        convert_to_numpy=True, 
        show_progress_bar=True,
        normalize_embeddings=True
    )
    index.add(new_embeddings)

    df_updated.to_pickle(CORPUS_DF_PATH)
    faiss.write_index(index, FAISS_INDEX_PATH)

    print(f"\n -- Mise à jour terminée")

if __name__ == "__main__":

    update_corpus()




