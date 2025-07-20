import nltk
import os

# On définit le chemin de destination à l'intérieur de notre application
# Ce dossier sera créé pendant le build et conservé avec le code
DOWNLOAD_DIR = 'app/nltk_data'

# On s'assure que le dossier existe
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

print(f"Téléchargement des ressources NLTK (punkt) dans le dossier : {DOWNLOAD_DIR}")
nltk.download('punkt', download_dir=DOWNLOAD_DIR)
print("Ressources NLTK téléchargées avec succès.")