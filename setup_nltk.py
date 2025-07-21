# setup_nltk.py

import nltk

# AJOUTEZ 'punkt_tab' à cette liste
packages = ['punkt', 'punkt_tab', 'stopwords']

for package in packages:
    try:
        # Cette vérification peut être simplifiée
        nltk.data.find(f'tokenizers/{package}')
        print(f"'{package}' is already downloaded.")
    except LookupError:
        print(f"Downloading '{package}'...")
        nltk.download(package, quiet=True) # L'option quiet évite trop de logs
        print(f"'{package}' downloaded successfully.")