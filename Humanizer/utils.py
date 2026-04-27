import random

def apply_zws_cloak(text: str):
    """Zero-Width Space Injection Algorithm."""
    zws = "\u200B"
    words = text.split()
    cloaked = []
    for word in words:
        if len(word) > 5 and random.random() < 0.1:
            pos = random.randint(1, len(word)-1)
            word = word[:pos] + zws + word[pos:]
        cloaked.append(word)
    return " ".join(cloaked)

def pii_masking(text: str):
    """Privacy Shield."""
    # Placeholder για Regex-based masking ονομάτων/τηλεφώνων
    return text