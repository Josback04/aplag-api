import nltk

# Ce script sera exécuté une seule fois pendant le build sur Railway
print("Téléchargement des ressources NLTK (punkt)...")
nltk.download('punkt')
print("Ressources NLTK téléchargées avec succès.")