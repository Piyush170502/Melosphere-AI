import streamlit as st
import requests
import pronouncing
import math
import random
import re

# ------------------------
# Helper: Translation
# ------------------------

def translate_text(text, target_lang):
    api_key = st.secrets.get("general", {}).get("GOOGLE_TRANSLATE_API_KEY", None)
    if not api_key:
        return "⚠️ Translation API key not found in Streamlit secrets. Please add it under [general] GOOGLE_TRANSLATE_API_KEY."
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {"q": text, "target": target_lang, "format": "text"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if "data" in data and "translations" in data["data"]:
            return data["data"]["translations"][0]["translatedText"]
        elif "error" in data:
            return f"API error: {data['error'].get('message','unknown')}"
        else:
            return f"Unexpected response: {data}"
    except Exception as e:
        return f"Error during translation: {e}"

# ------------------------
# Rhymes & Syllable helpers
# ------------------------

def get_rhymes(word):
    try:
        response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10', timeout=6)
        if response.status_code == 200:
            return [item['word'] for item in response.json()]
    except Exception:
        pass
    return []

def count_syllables_english(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for ch in word.lower() if ch in 'aeiou')

def count_syllables_heuristic(text):
    text = str(text)
    for ch in ",.!?;:-—()\"'":
        text = text.replace(ch, " ")
    words = [w for w in text.split() if w.strip()]
    syllables = 0
    for w in words:
        lw = w.lower()
        groups = 0
        prev_vowel = False
        for ch in lw:
            is_v = ch in "aeiouáàâäãåāéèêëēíìîïīóòôöõōúùûüūy"
            if is_v and not prev_vowel:
                groups += 1
            prev_vowel = is_v
        if groups == 0:
            groups = 1
        syllables += groups
    return syllables

def count_syllables_general(text, lang_code):
    if not text or not isinstance(text, str):
        return 0
    if lang_code.startswith("en"):
        words = [w for w in text.split() if w.strip()]
        return sum(count_syllables_english(w) for w in words)
    else:
        return count_syllables_heuristic(text)

# ------------------------
# Rhythmic Enhancement
# ------------------------

def rhythmic_translation_enhancement(original, translated):
    """
    Adjusts translation rhythm to match syllable count naturally.
    Adds gentle fillers ('oh', 'la', 'yeah') instead of repetition.
    """
    fillers = ["oh", "la", "yeah", "na", "ha"]
    orig_syll = count_syllables_general(original, "en")
    trans_syll = count_syllables_heuristic(translated)
    diff = orig_syll - trans_syll

    if diff > 0:
        # add subtle natural fillers, not repeating words
        extra = " ".join(random.choices(fillers, k=min(diff, 3)))
        translated = f"{translated} {extra}"
    elif diff < 0:
        # trim overly long translations gracefully
        words = translated.split()
        translated = " ".join(words[:max(1, len(words) + diff)])

    # placeholder for future stress/beat alignment
    translated = re.sub(r"\s+", " ", translated).strip()

    return translated, orig_syll, trans_syll, diff

# ------------------------
# Blending Strategies
# ------------------------

def interleave_words(original, translations_by_lang):
    tokenized = [t.split() for t in translations_by_lang]
    max_len = max(len(t) for t in tokenized) if tokenized else 0
    blended_tokens = []
    for i in range(max_len):
        for tok_list in tokenized:
            if i < len(tok_list):
                blended_tokens.append(tok_list[i])
    return " ".join(dict.fromkeys(blended_tokens))  # remove duplicates

def phrase_swap(original, translations_by_lang):
    segments = []
    for t in translations_by_lang:
        words = t.split()
        segments.append(words)
    if len(segments) == 1:
        return translations_by_lang[0]
    if len(segments) == 2:
        a, b = segments
        a_seg = a[:math.ceil(len(a) / 2)]
        b_seg = b[math.floor(len(b) / 2):]
        return " ".join(dict.fromkeys(a_seg + b_seg))
    assembled = []
    for idx, words in enumerate(segments):
        n = len(words)
        start = math.floor(idx * n / len(segments))
        end = math.floor((idx + 1) * n / len(segments))
        if start < end:
            assembled.extend(words[start:end])
        else:
            assembled.extend(words[: max(1, min(3, n))])
    return " ".join(dict.fromkeys(assembled))

def last_word_swap(original, translations_by_lang):
    orig_words = original.strip().split()
    if not orig_words:
        return original
    for t in translations_by_lang:
        tw = t.strip().split()
        if tw:
            new_last = tw[-1]
            return " ".join(dict.fromkeys(orig_words[:-1] + [new_last]))
    return original

# ------------------------
# Streamlit UI (Unchanged Polyglot)
# ------------------------

def main():
    st.set_page_config(page_title="Melosphere — Phase 2 (Polyglot Blending)", layout="wide")
    st.title("🎛️ Melosphere — Phase 2: Polyglot Lyric Blending")

    st.markdown("""
    This screen lets you generate *multiple* translations of a lyric line and blend them into a single multilingual lyric.
    - Pick 2 or more target languages.
    - Choose a blending mode and inspect syllable counts to preserve rhythm.
    """)

    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("Enter your lyric line (source language = English):", height=80)
    with col2:
        available_languages = {
            "Spanish": "es", "Kannada": "kn", "Tamil": "ta",
            "Malayalam": "ml", "Hindi": "hi", "Telugu": "te",
            "Japanese": "ja", "French": "fr", "Portuguese": "pt",
            "German": "de", "Korean": "ko"
        }
        selected = st.multiselect("Select 2+ target languages (for blending):",
                                  options=list(available_languages.keys()),
                                  default=["Spanish", "Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])
        enhance_rhythm = st.checkbox("✨ Rhythmic Enhancement", value=True)
        show_syllables = st.checkbox("Show syllable hints / rhythm warnings", value=True)
        show_rhymes = st.checkbox("Show English rhymes for the last word (only English)", value=True)

    if not lyric_line or not selected or len(selected) < 1:
        st.info("Enter a lyric line and select at least one language to see translations and blends.")
        return

    tgt_codes = [available_languages[l] for l in selected]
    translations = {}
    for lang_name, code in zip(selected, tgt_codes):
        trans = translate_text(lyric_line, code)
        if enhance_rhythm:
            trans, orig_s, trans_s, diff = rhythmic_translation_enhancement(lyric_line, trans)
        translations[lang_name] = trans

    st.subheader("Translations")
    trans_cols = st.columns(len(selected))
    for col, lang_name in zip(trans_cols, selected):
        with col:
            st.markdown(f"**{lang_name} ({available_languages[lang_name]})**")
            st.write(translations[lang_name])
            if show_syllables:
                sc = count_syllables_general(translations[lang_name], available_languages[lang_name])
                st.caption(f"Approx. syllables: {sc}")

    st.subheader("Blended Outputs")
    translations_list = [translations[name] for name in selected]
    if mode == "Interleave Words":
        blended = interleave_words(lyric_line, translations_list)
    elif mode == "Phrase Swap":
        blended = phrase_swap(lyric_line, translations_list)
    elif mode == "Last-Word Swap":
        blended = last_word_swap(lyric_line, translations_list)
    else:
        blended = lyric_line

    st.markdown("**Blended lyric preview:**")
    st.info(blended)

    if show_syllables:
        st.subheader("Rhythm / Syllable Analysis")
        source_syll = count_syllables_general(lyric_line, "en")
        st.write(f"Source (English) total syllables ≈ **{source_syll}**")
        for lang_name in selected:
            code = available_languages[lang_name]
            t = translations[lang_name]
            sc = count_syllables_general(t, code)
            diff = sc - source_syll
            if diff == 0:
                st.success(f"{lang_name}: {sc} syllables (matches source)")
            elif abs(diff) <= 2:
                st.warning(f"{lang_name}: {sc} syllables ({'+' if diff>0 else ''}{diff} vs source) — near match")
            else:
                st.error(f"{lang_name}: {sc} syllables ({'+' if diff>0 else ''}{diff} vs source) — large mismatch.")

    if show_rhymes:
        last_word = lyric_line.strip().split()[-1].lower() if lyric_line.strip().split() else ""
        if last_word:
            rhymes = get_rhymes(last_word)
            if rhymes:
                st.subheader(f"English rhymes for '{last_word}'")
                st.write(", ".join(rhymes))
            else:
                st.subheader("No English rhymes found")

    st.subheader("Export")
    st.write("You can copy the blended lyric below.")
    st.code(blended, language="text")
    st.download_button("Download blended lyric as .txt", blended, file_name="melosphere_blended_lyric.txt")

    st.markdown("""
    **Notes & limitations**
    - Syllable counts for non-English languages are heuristic and approximate.
    - Rhythmic enhancement now balances syllables with natural fillers (no repetition).
    - Placeholder for stress/beat alignment (to preserve musical phrasing) is built in.
    """)

if __name__ == "__main__":
    main()
