
"""
Strong content validator for detecting spam, gibberish, and inappropriate text.
Rejects nonsense sequences and allows only meaningful human-like writing.
"""

import re
from typing import Tuple


# Offensive words (standalone only)
BAD_WORDS = [
    'fuck', 'shit', 'bitch', 'asshole', 'cunt', 'whore'
]


# Words that indicate nonsense
KEYSMASH_SEQUENCES = [
    r'(?:asdf|jkl|qwe|asd|sdf|dfg|fgh|ghj|hjkl)',  # keyboard rolls
]


def contains_bad_words(text: str) -> bool:
    text_lower = text.lower()
    for word in BAD_WORDS:
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            return True
    return False


def looks_like_gibberish(text: str) -> bool:
    """
    Detects meaningless text by looking at:
    - Too many vowel-less words
    - Words containing mostly consonants
    - Nonsense character repetition
    - Keyboard-mash patterns
    - Repeated sequences like 'abcabcabc'
    """
    words = re.findall(r"[a-zA-Z']+", text)
    if not words:
        return True  # no real words at all

    # Detect character repetition ("aaaaaaa", "bbbbbbb")
    if re.search(r'(.)\1{5,}', text):
        return True

    # Detect repeated sequences ("dsdsdsds", "abcabcabc")
    if re.search(r'(.{2,4})\1{2,}', text):
        return True

    # Detect keyboard-mashing
    for seq in KEYSMASH_SEQUENCES:
        if re.search(seq, text.lower()):
            return True

    # Too many words with no vowels = gibberish
    vowel_less = sum(1 for w in words if not re.search(r'[aeiou]', w.lower()))
    if vowel_less > len(words) * 0.4:  # 40% of words vowel-less
        return True

    # Words that look like random noise (length ≥ 6 but no structure)
    noisy_words = 0
    for w in words:
        if len(w) >= 6 and re.search(r'[^aeiou]{5,}', w.lower()):
            noisy_words += 1
    if noisy_words >= 2:
        return True

    return False


def too_many_random_characters(text: str) -> bool:
    # Blocks texts with mostly non-letter characters
    letters = len(re.findall(r'[a-zA-Z]', text))
    non_letters = len(text) - letters
    if non_letters > len(text) * 0.5:
        return True
    return False


def validate_content(text: str, is_title=False) -> Tuple[bool, str]:
    if not text or not text.strip():
        return False, "Please write a review."

    text = text.strip()
    lower = text.lower()

    # 1. Profanity
    if contains_bad_words(lower):
        return False, "Please remove inappropriate language from your review."

    # Titles should not be blocked by full-sentence rules
    if is_title:
        # Still block pure gibberish or keyboard mashing
        if re.search(r"(.)\1{5,}", text):
            return False, "Please write a meaningful title."

        if re.search(r"[bcdfghjklmnpqrstvwxyz]{6,}", lower):
            return False, "Your title looks like gibberish."

        if re.search(r"(qwe|asd|sdf|dfg|fgh|jkl|kjh|poi|lkj)", lower):
            return False, "Your title looks like keyboard mashing."

        # Allow short titles like "BMW i7", "Good car", etc.
        return True, ""

    # ---------------------
    # FULL REVIEW VALIDATION
    # ---------------------

    # Excessive repeated characters
    if re.search(r"(.)\1{5,}", text):
        return False, "Your review contains excessive repeated characters."

    # Keyboard mashing
    if re.search(r"(qwe|asd|sdf|dfg|fgh|jkl|kjh|poi|lkj){1,}", lower):
        return False, "Your review looks like keyboard mashing."

    # Too many consonants in a row
    if re.search(r"[bcdfghjklmnpqrstvwxyz]{6,}", lower):
        return False, "Your review contains too much gibberish."

    # Too many vowel-less words
    words = re.findall(r"[a-zA-Z']+", text)
    vowel_less = sum(1 for w in words if not re.search(r"[aeiou]", w.lower()))
    if vowel_less >= 3:
        return False, "Your review contains too many non-words."

    # Too many short broken words
    short_bad = sum(1 for w in words if len(w) <= 3)
    if short_bad > len(words) * 0.6:
        return False, "Your review does not contain meaningful sentences."

    # Sentence structure requirement
    if not re.search(r"[a-zA-Z]{4,}\s+[a-zA-Z]{4,}", text):
        return False, "Your review must contain readable sentences."

    return True, ""
