# app.py
import streamlit as st
import os
import re
from google.cloud import translate_v2 as translate

# -----------------------------
# Set up Google Translate client
# -----------------------------
# Make sure you added your API key in Streamlit Secrets as:
# GOOGLE_API_KEY = "YOUR_API_KEY_HERE"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcloud_key.json"

# In Streamlit cloud, save your API key JSON content as a file
# This will let the client authenticate
import json
gcloud_key = json.loads(st.secrets["GOOGLE_API_KEY_JSON"])
with open("gcloud_key.json", "w") as f:
    json.dump(gcloud_key, f)

translate_client = translate.Client()

# -----------------------------
# Translation helper
# -----------------------------
def translate_text(text, target_lang):
    """Translate text into target_lang using Google Translate API"""
    if target_lang == "en":
        return text  # keep English as is
    try:
        result = translate_client.translate(text, target_language=target_lang)
        return result["translatedText"]
    except Exception as e:
        return f"[Error: {e}]"

# -----------------------------
# Polyglot blending logic
# -----------------------------
def polyglot_blend(sentence, languages):
    """
    Smooth polyglot blending:
    - Split sentence into phrases/clauses
    - Rotate languages per phrase
    - Preserve important English keywords
    """
    # Split by punctuation and spaces
    chunks = re.split(r'([,.!?])', sentence)
    chunks = [c.strip() for c in chunks if c.strip()]

    blended_chunks = []

    # Keywords to preserve in English
    keywords = ["love", "handmade", "somebody", "Girl"]

    for i, chunk in enumerate(chunks):
        tgt_lang = languages[i % len(languages)]
        translated = translate_text(chunk, tgt_lang)

        # Restore preserved keywords
        for k in keywords:
            if k in chunk:
                translated = re.sub(r'\b' + re.escape(k) + r'\b', k, translated)

        blended_chunks.append(translated)

    # Join chunks
    return " ".join(blended_chunks)

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🎵 Polyglot Lyric Blending App")

lyric_line = st.text_area("Enter a lyric line to blend:", "")

# Select languages to blend
available_languages = {
    "English": "en",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Japanese": "ja"
}

selected_langs = st.multiselect(
    "Select languages to blend (at least 2):",
    options=list(available_languages.keys()),
    default=["English", "Hindi", "Tamil"]
)

blend_button = st.button("Blend Lyric")

if blend_button:
    if lyric_line.strip() == "":
        st.warning("Please enter a lyric line.")
    elif len(selected_langs) < 2:
        st.warning("Select at least 2 languages for blending.")
    else:
        # Map selected names to language codes
        codes = [available_languages[l] for l in selected_langs]

        blended = polyglot_blend(lyric_line, codes)
        st.write("### 🎶 Blended Lyric Line:")
        st.success(blended)
