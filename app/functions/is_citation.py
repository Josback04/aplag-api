import re
def is_citation_or_reference(sentence):
    """Détecte si une phrase est probablement une citation ou une référence bibliographique."""
    sentence = sentence.strip()
    if not sentence or len(sentence.split()) < 5: return True
    if re.match(r'^\\s*[«\"“].+?[»\"”]\\s*$', sentence): return True
    if re.search(r'\\(\\s*[A-Za-z\\s\\.,]+\\s*,\\s*\\d{4}\\s*\\)', sentence): return True
    return False