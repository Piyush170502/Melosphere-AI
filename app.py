# app.py
import streamlit as st
import requests
from deep_translator import GoogleTranslator
import pronouncing
from langdetect import detect
import re

# -----------------------------
# Translation Functions
# -----------------------------
def translate(text, tgt_lang_code):
    """Translate a given text to the target language (skip English)."""
    try:
        if tgt_lang_code == 'en':
            return text
        translated = GoogleTranslator(source='auto', target=tgt_lang_code).translate(text)
        return translated
    except Exception:
        return text  # graceful fallback

def chunk_text(text, chunk_size=4):
    """
    Split text into small phrase-like chunks (approx. 4 words each).
    Keeps punctuation attached to last word of chunk.
    """
    words = re.findall(r"\b\w+\b[.,!?;']*", text)
    chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    return chunks

def translate_polyglot_line(line, target_languages):
    """
    Translates a line phrase-by-phrase into multiple languages,
    cycling through selected languages for smoother blending.
    """
    chunks = chunk_text(line)
    blended_chunks = []

    for i, chunk in enumerate(chunks):
        tgt_lang = target_languages[i % len(target_languages)]
        translated_chunk = translate(chunk, tgt_lang)
        blended_chunks.append(translated_chunk)

    # Join with space; capitalize first letter if needed
    blended_line = ' '.join(blended_chunks).strip()
    return blended_line[0].upper() + blended_line[1:] if blended_line else blended_line

# -----------------------------
# Rhymes & Syllable Functions
# -----------------------------
def get_rhymes(word):
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        rhymes = [item['word'] for item in response.json()]
        return rhymes
    return []

def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for char in word.lower() if char in 'aeiou')

# -----------------------------
# Streamlit App
# -----------------------------
def main():
    st.title("Melosphere AI - Lyrics without Limits 🎵")

    st.header("Phase 1: Translate & Rhyme")
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

    tgt_lang = st.selectbox("Select target language for translation:", list(languages.keys()))

    if lyric_line:
        words = lyric_line.strip().split()
        last_word = words[-1].lower()

        # Rhymes
        rhymes = get_rhymes(last_word)
        if rhymes:
            st.write(f"Rhymes for '{last_word}': {', '.join(rhymes)}")
        else:
            st.write(f"No rhymes found for '{last_word}'.")

        # Syllables
        syllables_per_word = {w: count_syllables(w) for w in words}
        total_syllables = sum(syllables_per_word.values())
        st.write(f"Syllables per word: {syllables_per_word}")
        st.write(f"Total syllables in your line: {total_syllables}")

        # Translation
        translation = translate(lyric_line, languages[tgt_lang])
        st.write(f"{tgt_lang} translation: {translation}")

    st.header("Phase 2: Polyglot Lyric Blending 🌍")
    blended_languages = st.multiselect(
        "Select languages for blended translation (include English for smoother results):",
        list(languages.keys()),
        default=["English", "Spanish", "Hindi"]
    )

    if lyric_line and blended_languages:
        blended_lang_codes = [languages[lang] for lang in blended_languages]
        blended_line = translate_polyglot_line(lyric_line, blended_lang_codes)
        st.write(f"**Blended lyric line:** {blended_line}")

if __name__ == "__main__":
    main()
