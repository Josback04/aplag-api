from rapidfuzz import fuzz
def calculate_lexical_metrics(s1, s2):
    """Calcule les scores de Levenshtein et Jaccard entre deux chaînes."""
   
    levenshtein_ratio = fuzz.ratio(s1, s2) / 100
    
    tokens1 = set(s1.lower().split())
    tokens2 = set(s2.lower().split())
    
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    jaccard_ratio = intersection / union if union != 0 else 0

    return {"levenshtein": levenshtein_ratio, "jaccard": jaccard_ratio}
