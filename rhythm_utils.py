import re
import random
import hashlib
import pronouncing
import logging

# Central clean_text function
def clean_text(text):
    """Normalize text for syllable counting and comparison."""
    if text is None:
        return ""
    t = str(text)
    # unify dashes and quotes
    t = t.replace("—", "-").replace("–", "-")
    # remove stray punctuation we don't want
    t = re.sub(r"[\"“”‘’]+", "", t)
    # preserve sentence-final punctuation for filler insertion logic
    t = t.strip()
    return t

# Unified syllable counter: uses pronouncing for en, heuristic otherwise
def count_syllables(text, lang_code="en"):
    """Count syllables in text. For English uses pronouncing where possible; fallback heuristic otherwise."""
    text = clean_text(text)
    if not text:
        return 0
    if lang_code and lang_code.startswith("en"):
        # split words and use pronouncing where possible
        words = [w for w in re.split(r"\s+", text) if w.strip()]
        sylls = 0
        for w in words:
            phones = pronouncing.phones_for_word(w.lower())
            if phones:
                try:
                    sylls += pronouncing.syllable_count(phones[0])
                except Exception:
                    sylls += _syllable_count_heuristic_word(w)
            else:
                sylls += _syllable_count_heuristic_word(w)
        return sylls
    else:
        # use heuristic for other languages
        words = [w for w in re.split(r"\s+", text) if w.strip()]
        return sum(_syllable_count_heuristic_word(w) for w in words)

def _syllable_count_heuristic_word(word):
    """Heuristic syllable count for a single word (simplified)."""
    lw = word.lower()
    lw = re.sub(r"[^a-záàâäãåāéèêëēíìîïīóòôöõōúùûüūyɪɔŋ]", "", lw)
    if not lw:
        return 0
    groups = 0
    prev_vowel = False
    for ch in lw:
        is_v = ch in "aeiouáàâäãåāéèêëēíìîïīóòôöõōúùûüūy"
        if is_v and not prev_vowel:
            groups += 1
        prev_vowel = is_v
    return groups if groups > 0 else 1

# Deterministic filler builder
_DEFAULT_FILLERS = ["oh", "la", "yeah", "na", "hey", "mmm"]

def build_fillers(diff, max_fillers=3, seed_text=None):
    """Deterministically pick fillers based on seed_text hash and the diff number."""
    k = min(max_fillers, max(0, diff))
    if k == 0:
        return ""
    # Seed randomness deterministically from seed_text
    seed = 0
    if seed_text is not None:
        seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    rnd = random.Random(seed)
    if k <= len(_DEFAULT_FILLERS):
        chosen = rnd.sample(_DEFAULT_FILLERS, k)
    else:
        # sample with replacement if k > available fillers
        chosen = [rnd.choice(_DEFAULT_FILLERS) for _ in range(k)]
    return " ".join(chosen)

def insert_fillers_safely(translated_text, fillers_str):
    """Insert fillers into translated_text safely without breaking punctuation badly."""
    if not fillers_str:
        return translated_text
    t = translated_text.strip()
    # If there is punctuation at the end, insert before it
    m = re.search(r'([.!?])\s*$', t)
    if m:
        base = t[:m.start()].rstrip()
        punct = m.group(1)
        return f"{base}, {fillers_str}{punct}"
    else:
        last_comma = t.rfind(',')
        if last_comma != -1 and last_comma < len(t) - 1:
            return f"{t}, {fillers_str}"
        return f"{t}, {fillers_str}"

def rhythmic_translation_enhancement(original, translated, max_fillers=3):
    """Keep original logic but use centralized functions and deterministic fillers."""
    orig_syllables = count_syllables(original, "en")
    trans_syll_before = count_syllables(translated, "xx")
    diff = orig_syllables - trans_syll_before
    if diff <= 0:
        enhanced = translated.strip()
        trans_syll_after = trans_syll_before
    else:
        fillers_str = build_fillers(diff, max_fillers=max_fillers, seed_text=translated + original)
        enhanced = insert_fillers_safely(translated, fillers_str)
        trans_syll_after = count_syllables(enhanced, "xx")
    enhanced = re.sub(r"\s+", " ", enhanced).strip()
    return enhanced, orig_syllables, trans_syll_before, trans_syll_after, diff
