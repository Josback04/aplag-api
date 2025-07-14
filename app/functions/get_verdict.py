import difflib

def get_highlighted_diff_html(s1, s2):
    """Génère un affichage HTML des différences entre deux chaînes."""
    s1_words, s2_words = s1.split(), s2.split()
    matcher = difflib.SequenceMatcher(None, s1_words, s2_words)
    output1, output2 = [], []
    
    opcodes = matcher.get_opcodes()
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            output1.append(" ".join(f"<b>{word}</b>" for word in s1_words[i1:i2]))
            output2.append(" ".join(f"<b>{word}</b>" for word in s2_words[j1:j2]))
        else:
            if tag in ('replace', 'delete'):
                output1.append(" ".join(f"<span style='color:lightgray; text-decoration: line-through;'>{word}</span>" for word in s1_words[i1:i2]))
            if tag in ('replace', 'insert'):
                output2.append(" ".join(f"<i style='background-color: #d4edda;'>{word}</i>" for word in s2_words[j1:j2]))

    return " ".join(output1), " ".join(output2)

def get_final_verdict(cross_score, lexical_metrics, ngram_score):
    """Calcule un score composite et retourne un verdict."""
    W_CROSS, W_LEV, W_JAC, W_NGRAM = 0.65, 0.15, 0.15, 0.15
    
    composite_score = (W_CROSS * cross_score) + \
                      (W_LEV * lexical_metrics['levenshtein']) + \
                      (W_JAC * lexical_metrics['jaccard']) + \
                      (W_NGRAM * ngram_score)

    verdict = "Non suspect"
    if composite_score >= 0.85:
        verdict = "Texte très similaire / Copié-collé"
    elif 0.7 <= composite_score < 0.85:
        verdict = "Forte suspicion de paraphrase"
    elif 0.6 <= composite_score < 0.7:
        verdict = "Similarité thématique, potentiellement paraphrasé"
        
    return verdict, composite_score