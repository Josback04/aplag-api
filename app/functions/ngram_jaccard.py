def calculate_ngram_jaccard(s1, s2, n=2):
    """Calcule le score de Jaccard basé sur les n-grammes."""
    s1_tokens = s1.lower().split()
    s2_tokens = s2.lower().split()

    ngrams1 = set([' '.join(s1_tokens[i:i+n]) for i in range(len(s1_tokens) - n + 1)])
    ngrams2 = set([' '.join(s2_tokens[i:i+n]) for i in range(len(s2_tokens) - n + 1)])

    if not ngrams1 or not ngrams2:
        return 0.0
    
    intersection = len(ngrams1.intersection(ngrams2))
    union = len(ngrams1.union(ngrams2))

    return intersection / union if union != 0 else 0