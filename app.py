import streamlit as st
import requests
from deep_translator import GoogleTranslator
import pronouncing
import os
from gtts import gTTS
import tempfile
from transformers import pipeline

# --------------------------
# Helper Functions
# --------------------------

# 1️⃣ Translation
def translate(text, tgt_lang_code):
    try:
        translated = GoogleTranslator(source='auto', target=tgt_lang_code).translate(text)
        return translated
    except Exception as e:
        return f"Error in translation: {e}"

# 2️⃣ Rhyme Suggestion
def get_rhymes(word):
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        rhymes = [item['word'] for item in response.json()]
        return rhymes
    else:
        return []

# 3️⃣ Syllable Counting
def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    else:
        # fallback simple vowel count
        return sum(1 for char in word.lower() if char in 'aeiou')

def count_total_syllables(line):
    words = line.strip().split()
    return sum(count_syllables(w) for w in words)

# 4️⃣ Rhythmic Adjustment (basic version)
def rhythmic_adjustment(translated_line, target_syllables):
    # For prototype: simple retry message
    current_syllables = count_total_syllables(translated_line)
    if abs(current_syllables - target_syllables) > 2:
        return f"[Rhythm Alert] Current syllables: {current_syllables}, target: {target_syllables}"
    else:
        return translated_line

# 5️⃣ Pronunciation Guide
def generate_pronunciation_audio(text, lang_code):
    tts = gTTS(text=text, lang=lang_code)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp_file.name)
    return tmp_file.name

# 6️⃣ Emotion Adaptation (basic sentiment)
sentiment_analyzer = pipeline("sentiment-analysis")
def emotional_adaptation(translated_line, source_line):
    # Basic prototype: if English line is negative, mark translated as negative
    sentiment = sentiment_analyzer(source_line)[0]
    if sentiment['label'] == 'NEGATIVE':
        return f"[Emotion Adjusted] {translated_line} (tone: negative)"
    elif sentiment['label'] == 'POSITIVE':
        return f"[Emotion Adjusted] {translated_line} (tone: positive)"
    else:
        return translated_line

# 7️⃣ AI-powered Rhyme / Metaphor Suggestions (placeholder for API/LLM)
def ai_rhyme_metaphor_engine(target_word, lang_code="ta"):
    # Placeholder: return rhymes from Datamuse for now (improve with LLM later)
    rhymes = get_rhymes(target_word)
    return rhymes[:5] if rhymes else ["No rhymes found"]

# --------------------------
# Streamlit UI
# --------------------------

st.title("Melosphere AI - Core Lyric Translation & Enhancement")

# Input English lyrics
english_lyric = st.text_area("Enter English lyric line or song:")

# Language selection
languages = {
    "Tamil": "ta",
    "Hindi": "hi",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Telugu": "te",
    "Japanese": "ja",
    "Spanish": "es"
}
tgt_lang = st.selectbox("Select target language:", list(languages.keys()))

if english_lyric:
    # -----------------------
    # Step 1: Translation
    # -----------------------
    translated_line = translate(english_lyric, languages[tgt_lang])
    st.subheader("Translated Lyric")
    st.write(translated_line)

    # -----------------------
    # Step 2: Rhythmic Alignment
    # -----------------------
    original_syllables = count_total_syllables(english_lyric)
    rhythmic_line = rhythmic_adjustment(translated_line, original_syllables)
    st.subheader("Rhythmic Check / Adjustment")
    st.write(rhythmic_line)

    # -----------------------
    # Step 3: Pronunciation Guide
    # -----------------------
    st.subheader("Pronunciation Guide")
    audio_file = generate_pronunciation_audio(translated_line, languages[tgt_lang])
    st.audio(audio_file, format="audio/mp3")
    st.write("Play above to hear pronunciation.")

    # -----------------------
    # Step 4: Regional Emotion Adaptation
    # -----------------------
    adapted_line = emotional_adaptation(translated_line, english_lyric)
    st.subheader("Emotion-Adjusted Translation")
    st.write(adapted_line)

    # -----------------------
    # Step 5: AI Rhyme & Metaphor Suggestions
    # -----------------------
    st.subheader("AI Rhyme / Metaphor Suggestions")
    words = translated_line.strip().split()
    last_word = words[-1].lower()
    rhymes_suggestions = ai_rhyme_metaphor_engine(last_word, languages[tgt_lang])
    st.write(f"Suggested rhymes / creative variants for '{last_word}': {', '.join(rhymes_suggestions)}")
