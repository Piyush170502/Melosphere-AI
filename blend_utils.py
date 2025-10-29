import math
import random
from .rhythm_utils import clean_text

def interleave_words(original, translations_by_lang):
    """Interleave words across provided translations. Preserves order within each language."""
    tokenized = [t.split() for t in translations_by_lang]
    max_len = max((len(t) for t in tokenized), default=0)
    blended_tokens = []
    for i in range(max_len):
        for tok_list in tokenized:
            if i < len(tok_list):
                blended_tokens.append(tok_list[i])
    return " ".join(blended_tokens)

def phrase_swap(original, translations_by_lang):
    """Swap halves (or slices) of translated phrases. Keeps original behavior."""
    segments = []
    for t in translations_by_lang:
        words = [w for w in t.split() if w.strip()]
        segments.append(words)
    if len(segments) == 0:
        return ""
    if len(segments) == 1:
        return translations_by_lang[0]
    if len(segments) == 2:
        a, b = segments
        a_seg = a[:math.ceil(len(a) / 2)]
        b_seg = b[math.floor(len(b) / 2):]
        return " ".join(a_seg + b_seg)
    assembled = []
    for idx, words in enumerate(segments):
        n = len(words)
        start = math.floor(idx * n / len(segments))
        end = math.floor((idx + 1) * n / len(segments))
        if start < end:
            assembled.extend(words[start:end])
        else:
            assembled.extend(words[: max(1, min(3, n))])
    return " ".join(assembled)

def last_word_swap(original, translations_by_lang):
    """Replace last word of original with the last word from the first non-empty translation."""
    orig_words = [w for w in original.strip().split() if w.strip()]
    if not orig_words:
        return original
    for t in translations_by_lang:
        tw = [w for w in t.strip().split() if w.strip()]
        if tw:
            new_last = tw[-1]
            return " ".join(orig_words[:-1] + [new_last])
    return original

def remove_consecutive_duplicates(text):
    words = text.split()
    if not words:
        return ""
    out = [words[0]]
    for w in words[1:]:
        if w != out[-1]:
            out.append(w)
    return " ".join(out)
