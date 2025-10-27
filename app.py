# app.py
import streamlit as st
import requests
from deep_translator import GoogleTranslator
import pronouncing
from langdetect import detect

# -----------------------------
# Translation Functions
# -----------------------------
def translate(text, tgt_lang_code):
    """Translate a given text to the target language"""
    try:
        # If target language is English, just return the same text
        if tgt_lang_code == 'en':
            return text
        translated = GoogleTranslator(source='auto', target=tgt_lang_code).translate(text)
        return translated
    except Exception as e:
        return f"Error in translation: {e}"

def translate_blended_line(line, target_languages):
    """
    Translate a line into multiple languages (polyglot blending).
    Cycles through the selected languages word by word.
    """
    words = line.strip().split()
    blended_line = []
    for i, word in enumerate(words):
        tgt_lang = target_languages[i % len(target_languages)]
        translated_word = translate(word, tgt_lang)
        blended_line.append(translated_word)
    return " ".join(blended_line)

# -----------------------------
# Rhymes & Syllable Functions
# -----------------------------
def get_rhymes(word):
    """Fetch rhymes for a given word from Datamuse API"""
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        rhymes = [item['word'] for item in response.json()]
        return rhymes
    return []

def count_syllables(word):
    """Count syllables using pronouncing library (fallback to vowels)"""
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

        # Syllable counts
        syllables_per_word = {w: count_syllables(w) for w in words}
        total_syllables = sum(syllables_per_word.values())
        st.write(f"Syllables per word: {syllables_per_word}")
        st.write(f"Total syllables in your line: {total_syllables}")

        # Translation
        translation = translate(lyric_line, languages[tgt_lang])
        st.write(f"{tgt_lang} translation: {translation}")

    st.header("Phase 2: Polyglot Lyric Blending 🌍")
    blended_languages = st.multiselect(
        "Select target languages for blended translation (you can include English):",
        list(languages.keys()),
        default=["English", "Spanish", "Hindi"]
    )

    if lyric_line and blended_languages:
        blended_lang_codes = [languages[lang] for lang in blended_languages]
        blended_line = translate_blended_line(lyric_line, blended_lang_codes)
        st.write(f"**Blended lyric line:** {blended_line}")

if __name__ == "__main__":
    main()
