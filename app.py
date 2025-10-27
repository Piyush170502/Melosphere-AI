# app.py
import streamlit as st
import requests
from deep_translator import GoogleTranslator
import pronouncing
import re
import random

# -----------------------------
# Translation Functions
# -----------------------------
def translate(text, tgt_lang_code):
    """Translate text to target language, skip if English."""
    try:
        if tgt_lang_code == "en":
            return text
        return GoogleTranslator(source="auto", target=tgt_lang_code).translate(text)
    except Exception:
        return text  # graceful fallback

def smart_chunk_text(text):
    """
    Break text into meaningful segments using punctuation and connectors.
    """
    # Split by punctuation and keep connectors
    segments = re.split(r'([,.;!?])', text)
    chunks = []
    buffer = ""
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        buffer += (" " + seg).strip()
        # Chunk around punctuation or about every 5 words
        if any(p in seg for p in [".", ",", ";", "!", "?"]) or len(buffer.split()) > 5:
            chunks.append(buffer.strip())
            buffer = ""
    if buffer:
        chunks.append(buffer.strip())
    return chunks

def clean_blended_line(line):
    """Fix spacing, punctuation, and capitalization in blended result."""
    line = re.sub(r'\s+([.,!?])', r'\1', line)
    line = re.sub(r'\s+', ' ', line).strip()
    if line:
        line = line[0].upper() + line[1:]
    return line

def translate_polyglot_line(line, target_languages):
    """
    Enhanced polyglot translator:
    - Keeps some phrases in English.
    - Translates selected segments phrase-by-phrase.
    - Balances frequency of English vs others.
    """
    chunks = smart_chunk_text(line)
    blended_chunks = []

    for i, chunk in enumerate(chunks):
        # More chance to keep English for connectors
        if len(target_languages) == 1 or random.random() < 0.5:
            tgt_lang = "en"
        else:
            tgt_lang = random.choice([lang for lang in target_languages if lang != "en"])

        translated_chunk = translate(chunk, tgt_lang)
        blended_chunks.append(translated_chunk)

    blended_line = " ".join(blended_chunks)
    return clean_blended_line(blended_line)

# -----------------------------
# Rhyme & Syllable Functions
# -----------------------------
def get_rhymes(word):
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        return [item["word"] for item in response.json()]
    return []

def count_syllables(word):
    import pronouncing
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for c in word.lower() if c in "aeiou")

# -----------------------------
# Streamlit App
# -----------------------------
def main():
    st.title("Melosphere AI — Lyrics Without Limits 🎶")

    st.header("Phase 1 — Translation & Rhyme")
    lyric_line = st.text_input("Enter your lyric line (English):")

    languages = {
        "English": "en",
        "Spanish": "es",
        "Kannada": "kn",
        "Tamil": "ta",
        "Malayalam": "ml",
        "Hindi": "hi",
        "Telugu": "te",
        "Japanese": "ja",
    }

    tgt_lang = st.selectbox("Select a target language for single translation:", list(languages.keys()))

    if lyric_line:
        words = lyric_line.strip().split()
        last_word = words[-1].lower()

        # Rhymes
        rhymes = get_rhymes(last_word)
        if rhymes:
            st.write(f"Rhymes for **{last_word}**: {', '.join(rhymes)}")
        else:
            st.write(f"No rhymes found for **{last_word}**.")

        # Syllables
        syllables = {w: count_syllables(w) for w in words}
        st.write("Syllables per word:", syllables)
        st.write("Total syllables:", sum(syllables.values()))

        # Translation
        st.write(f"**{tgt_lang} translation:** {translate(lyric_line, languages[tgt_lang])}")

    st.header("Phase 2 — Enhanced Polyglot Lyric Blending 🌍")
    blended_langs = st.multiselect(
        "Select languages to blend (include English for best results):",
        list(languages.keys()),
        default=["English", "Spanish", "Hindi", "Tamil"]
    )

    if lyric_line and blended_langs:
        codes = [languages[l] for l in blended_langs]
        blended = translate_polyglot_line(lyric_line, codes)
        st.write("### **Blended Lyric Line:**")
        st.success(blended)

if __name__ == "__main__":
    main()
