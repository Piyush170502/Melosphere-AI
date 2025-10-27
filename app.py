import streamlit as st
import requests
import pronouncing
from google.cloud import translate

# -----------------------------
# Load Google Translate API Key
# -----------------------------
import os

# Option 1: Use environment variable (recommended)
# export GOOGLE_API_KEY="YOUR_API_KEY" in terminal
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", None)  # safer in Streamlit sharing

# Initialize client
client = translate.TranslationServiceClient(client_options={"api_key": GOOGLE_API_KEY})
PROJECT_ID = "your-google-cloud-project-id"
LOCATION = "global"

def translate_text(text, target_lang):
    parent = f"projects/{eighth-pursuit-476416-c8}/locations/{LOCATION}"
    try:
        response = client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "target_language_code": target_lang,
            }
        )
        return response.translations[0].translated_text
    except Exception as e:
        return f"Error in translation: {e}"

# -----------------------------
# Rhymes & syllables functions
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
    else:
        return sum(1 for char in word.lower() if char in 'aeiou')

# -----------------------------
# Polyglot lyric blending
# -----------------------------
def translate_polyglot_line(line, langs):
    """
    Splits the line into words and cycles through selected languages.
    """
    words = line.strip().split()
    blended_chunks = []
    for i, word in enumerate(words):
        lang = langs[i % len(langs)]
        if lang == "en":
            blended_chunks.append(word)
        else:
            translated_word = translate_text(word, lang)
            blended_chunks.append(translated_word)
    return " ".join(blended_chunks)

# -----------------------------
# Streamlit app
# -----------------------------
def main():
    st.title("Melosphere AI - Lyrics without limits (Google Translate)")
    
    lyric_line = st.text_input("Enter your Lyric Line (English):")
    
    languages = {
        "English": "en",
        "Hindi": "hi",
        "Tamil": "ta",
        "Telugu": "te",
        "Malayalam": "ml",
        "Japanese": "ja",
    }

    # Multi-select for polyglot blending
    blended_langs = st.multiselect(
        "Select languages for polyglot blending (cycle through words):",
        list(languages.keys()),
        default=["English", "Hindi", "Tamil"]
    )

    if lyric_line:
        words = lyric_line.strip().split()
        last_word = words[-1].lower()
        rhymes = get_rhymes(last_word)
        if rhymes:
            st.write(f"Rhymes for '{last_word}': {', '.join(rhymes)}")
        else:
            st.write(f"No rhymes found for '{last_word}'.")

        syllables_per_word = {w: count_syllables(w) for w in words}
        total_syllables = sum(syllables_per_word.values())
        st.write(f"Syllables per word: {syllables_per_word}")
        st.write(f"Total syllables in your line: {total_syllables}")

        if blended_langs:
            codes = [languages[l] for l in blended_langs]
            blended_line = translate_polyglot_line(lyric_line, codes)
            st.write("### **Blended Lyric Line:**")
            st.success(blended_line)

        # Optionally show full translations
        st.write("### **Full Translations:**")
        for lang_name, code in languages.items():
            translation = translate_text(lyric_line, code)
            st.write(f"{lang_name}: {translation}")

if __name__ == "__main__":
    main()
