import os

import fitz  # PyMuPDF
import nltk
import nltk.downloader
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder

from .functions.lexical_metrics import calculate_lexical_metrics
from .functions.get_verdict import get_final_verdict, get_highlighted_diff_html
from .functions.is_citation import is_citation_or_reference
from .functions.ngram_jaccard import calculate_ngram_jaccard
# ==============================================================================
# 1. CONFIGURATION DES CHEMINS
#    (Assurez-vous que ces chemins sont corrects par rapport à la racine du projet)
# ==============================================================================
BASE_DIR = os.path.dirname(__file__)
CORPUS_DIR = os.path.join(BASE_DIR, "corpus")

BI_ENCODER_NAME = 'sentence-transformers/msmarco-distilbert-base-v4'
CROSS_ENCODER_NAME = 'antoinelouis/crossencoder-camemberta-base-mmarcoFR'
FAISS_INDEX_PATH = os.path.join(CORPUS_DIR, 'corpus_doc.index')
CORPUS_DF_PATH = os.path.join(CORPUS_DIR, 'corpus_dataframe_doc.pkl')
TEXT_COLUMN = 'content_block'
SOURCE_COLUMN = 'title'

# S'assurer que le tokenizer 'punkt' de NLTK est disponible
try:
    nltk.data.find('tokenizers/punkt')
except Exception :
    nltk.download('punkt')


def load_bi_encoder():
    """Charge le modèle Bi-Encoder."""
    return SentenceTransformer(BI_ENCODER_NAME)

def load_cross_encoder():
    """Charge le modèle Cross-Encoder."""
    return CrossEncoder(CROSS_ENCODER_NAME)

def load_faiss_index():
    """Charge l'index FAISS depuis le disque."""
    if not os.path.exists(FAISS_INDEX_PATH):
        raise FileNotFoundError(f"L'index FAISS est introuvable au chemin : {FAISS_INDEX_PATH}")
    return faiss.read_index(FAISS_INDEX_PATH)

def load_corpus_dataframe():
    """Charge le DataFrame du corpus depuis le disque."""
    if not os.path.exists(CORPUS_DF_PATH):
        raise FileNotFoundError(f"Le DataFrame du corpus est introuvable au chemin : {CORPUS_DF_PATH}")
    return pd.read_pickle(CORPUS_DF_PATH)

# ==============================================================================
# 2. FONCTIONS DE CHARGEMENT DES RESSOURCES
#    (Appelées une seule fois au démarrage de l'API)
# ==============================================================================


# ==============================================================================
# 4. FONCTION PRINCIPALE D'ANALYSE
# ==============================================================================

def analyze_pdf_for_plagiarism(file_path: str, bi_encoder, cross_encoder, index, df_corpus, top_k_retrieve=20, min_verdict_score=0.6):
    """
    Fonction principale qui orchestre l'analyse de plagiat d'un fichier PDF.
    Elle prend les modèles pré-chargés en arguments pour être efficace.
    """
    try:
        # --- 1. EXTRACTION ET FILTRAGE DU TEXTE DU PDF ---
        doc = fitz.open(file_path)
        full_text = "".join(page.get_text() for page in doc)
        doc.close()

        if not full_text.strip():
            return {"message": "Le document PDF est vide ou ne contient pas de texte."}

        all_sentences = nltk.sent_tokenize(full_text, language='french')
        
        sentences_to_analyze = [s for s in all_sentences if not is_citation_or_reference(s)]
        
        if not sentences_to_analyze:
            return {"message": "Aucune phrase pertinente à analyser après filtrage."}

        # --- 2. ÉTAPE DE "RETRIEVE" (Bi-Encoder) ---
        query_embeddings = bi_encoder.encode(sentences_to_analyze, convert_to_numpy=True, show_progress_bar=True, normalize_embeddings=True)
        distances, indices = index.search(query_embeddings, top_k_retrieve)

        # --- 3. ÉTAPE DE "RE-RANK" ET ANALYSE COMPOSITE ---
        all_findings = []
        for i, query_sentence in enumerate(sentences_to_analyze):
            
            # Créer les paires pour le cross-encoder
            retrieved_hits = [{'corpus_id': idx, 'sentence': df_corpus.iloc[idx][TEXT_COLUMN]} for idx in indices[i]]
            cross_inp = [[query_sentence, hit['sentence']] for hit in retrieved_hits]
            
            # Prédiction avec le Cross-Encoder
            cross_scores = cross_encoder.predict(cross_inp, show_progress_bar=True)
            
            # Trouver le meilleur score
            best_hit_idx = np.argmax(cross_scores)
            best_hit = retrieved_hits[best_hit_idx]
            best_hit['cross_score'] = cross_scores[best_hit_idx]

            # Calcul des métriques additionnelles
            lexical_metrics = calculate_lexical_metrics(query_sentence, best_hit['sentence'])
            ngram_score = calculate_ngram_jaccard(query_sentence, best_hit['sentence'], n=3)
            
            # Verdict final
            verdict, composite_score = get_final_verdict(best_hit['cross_score'], lexical_metrics, ngram_score)
            
            # On ne garde que les résultats dépassant un certain seuil de suspicion
            if composite_score >= min_verdict_score:
                html_diff = get_highlighted_diff_html(query_sentence, best_hit['sentence'])
                source_document = df_corpus.iloc[best_hit['corpus_id']][SOURCE_COLUMN]

                finding = {
                    "phrase_suspecte": query_sentence,
                    "score_composite": round(float(composite_score), 3),
                    "verdict": verdict,
                    "details": {
                        "score_cross_encoder": round(float(best_hit['cross_score']), 3),
                        **lexical_metrics,
                        "score_ngram_jaccard": round(float(ngram_score), 3)
                    },
                    "source_trouvee": best_hit['sentence'],
                    "document_source": source_document,
                    "html_diff_suspecte": html_diff[0],
                    "html_diff_source": html_diff[1]
                }
                all_findings.append(finding)
        
        # --- 4. RAPPORT FINAL ---
        total_analyzed = len(sentences_to_analyze)
        total_suspect = len(all_findings)
        suspicion_ratio = total_suspect / total_analyzed if total_analyzed > 0 else 0

        final_report = {
            "summary": {
                "phrases_analysees": total_analyzed,
                "phrases_suspectes": total_suspect,
                "ratio_suspicion": f"{suspicion_ratio:.1%}"
            },
            "findings": sorted(all_findings, key=lambda x: x['score_composite'], reverse=True)
        }
        
        return final_report

    except Exception as e:
        # Remonter l'erreur pour que FastAPI la gère
        raise e