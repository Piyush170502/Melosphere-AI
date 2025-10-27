import streamlit as st
import json
import os
from google.cloud import translate_v2 as translate
import random

# -----------------------------
# Set up Google Translate client
# -----------------------------

# Load secret JSON and write to a temp file
gcloud_key = json.loads(st.secrets["GOOGLE_API_KEY_JSON"])
with open("gcloud_key.json", "w") as f:
    json.dump(gcloud_key, f)

# Set environment variable for Google SDK
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcloud_key.json"

translate_client = translate.Client()

# -----------------------------
# Language codes for blending
# -----------------------------
languages = {
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Japanese": "ja",
    "English": "en"
}

# -----------------------------
# Helper Functions
# -----------------------------
def translate_text(text, target_lang):
    """Translate a text string to a target language using Google Translate."""
    if target_lang == "en":
        return text  # Keep English as-is
    result = translate_client.translate(text, target_language=target_lang)
    return result["translatedText"]

def polyglot_blend(text, blend_languages, intensity=2):
    """
    Blend a text line into multiple languages.
    :param text: original English line
    :param blend_languages: list of language codes
    :param intensity: number of words to translate per language
    """
    words = text.split()
    blended_words = []

    for i, word in enumerate(words):
        # Randomly pick a language based on intensity
        if blend_languages and random.random() < (intensity / 10):
            lang = random.choice(blend_languages)
            translated_word = translate_text(word, lang)
            blended_words.append(translated_word)
        else:
            blended_words.append(word)
    return " ".join(blended_words)

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Polyglot Lyric Blending", layout="wide")
st.title("🎵 Polyglot Lyric Blending")

st.write(
    "Enter your lyric line in English, and blend it with multiple languages "
    "like Hindi, Tamil, Telugu, Malayalam, and Japanese!"
)

lyric_line = st.text_input("Enter English lyric line:")

st.write("### Select languages for blending:")
selected_langs = st.multiselect(
    "Languages",
    options=list(languages.keys()),
    default=["Hindi", "Tamil", "Telugu", "Malayalam", "Japanese"]
)

intensity = st.slider(
    "Blending intensity (higher = more words translated):", min_value=1, max_value=10, value=3
)

if st.button("Blend Lyric"):
    if lyric_line.strip() == "":
        st.warning("Please enter a lyric line first.")
    else:
        blend_codes = [languages[lang] for lang in selected_langs]
        blended_line = polyglot_blend(lyric_line, blend_codes, intensity)
        st.success(blended_line)
