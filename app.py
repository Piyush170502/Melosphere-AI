# app.py
import streamlit as st
import requests
from deep_translator import GoogleTranslator
import pronouncing
import re
import random
import time

# -----------------------------
# Translation Functions
# -----------------------------
def translate(text, tgt_lang_code, retries=2):
    """Translate text safely, skip if English or empty."""
    if not text or not isinstance(text, str):
        return ""
    try:
        if tgt_lang_code == "en":
            return text
        result = GoogleTranslator(source="auto", target=tgt_lang_code).translate(text)
        if result is None or not isinstance(result, str):
            raise ValueError("Empty translation result")
        return result
    except Exception:
        if retries > 0:
            time.sleep(0.5)
            return translate(text, tgt_lang_code, retries - 1)
        return text  # fallback to original text

def smart_chunk_text(text):
    """Split text into meaningful segments using punctuation and structure."""
    segments = re.split(r'([,.;!?])', text)
    chunks, buffer = [], ""
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        buffer += (" " + seg).strip()
        if any(p in seg for p in [".", ",", ";", "!", "?"]) or len(buffer.split()) > 5:
            chunks.append(buffer.strip())
            buffer = ""
    if buffer:
        chunks.append(buffer.strip())
    return chunks

def clean_blended_line(line):
    """Fix spacing and capitalization for final blended line."""
    if not line:
        return ""
    line = re.sub(r'\s+([.,!?])', r'\1', line)
    line = re.sub(r'\s+', ' ', line).strip()
    return line[0].upper() + line[1:] if line else line

def translate_polyglot_line(line, target_languages, creativity=0.5):
    """
    Polyglot lyric blending with creativity control.
    - creativity: 0 → mostly English, 1 → heavy multilingual.
    """
    chunks = smart_chunk_text(line)
    blended_chunks = []

    for chunk in chunks:
        # Weighted chance to switch from English to another language
        if len(target_languages) == 1 or random.random() > creativity:
            tgt_lang = "en"
        else:
            tgt_lang = random.choice([lang for lang in target_languages if lang != "en"])

        translated_chunk = translate(chunk, tgt_lang)
        blended_chunks.append(str(translated_chunk) if translated_chunk else chunk)

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
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for c in word.lower() if c in "aeiou")

# -----------------------------
# Streamlit App
# -----------------------------
def main():
    st.title("🎵 Melosphere AI — Lyrics Without Limits 🌍")

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

    st.header("Phase 2 — Enhanced Polyglot Lyric Blending 🌐")

    blended_langs = st.multiselect(
        "Select languages to blend (include English for smoother flow):",
        list(languages.keys()),
        default=["English", "Spanish", "Hindi", "Tamil"]
    )

    creativity = st.slider(
        "🎨 Creativity Level (0 = Mostly English, 1 = Full Multilingual Remix)",
        min_value=0.0, max_value=1.0, value=0.5, step=0.1
    )

    if lyric_line and blended_langs:
        codes = [languages[l] for l in blended_langs]
        blended = translate_polyglot_line(lyric_line, codes, creativity)
        st.write("### **Blended Lyric Line:**")
        st.success(blended)

if __name__ == "__main__":
    main()
