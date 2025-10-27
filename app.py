import streamlit as st
import requests
from deep_translator import GoogleTranslator
import pronouncing
import os
from gtts import gTTS
import tempfile
from transformers import pipeline
import openai

# --------------------------
# OpenAI API Key (set as environment variable)
# --------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

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

# 2️⃣ Syllable Counting
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

# 3️⃣ Rhythmic Adjustment (enhanced)
def rhythmic_adjustment(translated_line, target_syllables, lang_code):
    current_syllables = count_total_syllables(translated_line)
    if abs(current_syllables - target_syllables) > 1:
        # Use GPT to rephrase for rhythm
        prompt = (
            f"Rephrase this {lang_code} lyric to have approximately {target_syllables} syllables, "
            f"keeping meaning, emotion, and rhyme: '{translated_line}'"
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        rephrased_line = response['choices'][0]['message']['content'].strip()
        return rephrased_line
    else:
        return translated_line

# 4️⃣ Pronunciation Guide
def generate_pronunciation_audio(text, lang_code):
    tts = gTTS(text=text, lang=lang_code)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp_file.name)
    return tmp_file.name

# 5️⃣ Emotion Adaptation (enhanced)
sentiment_analyzer = pipeline("sentiment-analysis")

regional_synonyms = {
    "ta": {"love": "அன்பு", "heart": "இதயம்", "sad": "துயரம்"},
    "hi": {"love": "प्यार", "heart": "दिल", "sad": "उदासी"},
    "kn": {"love": "ಪ್ರೇಮ", "heart": "ಹೃದಯ", "sad": "ದುಃಖ"},
    "ml": {"love": "സ്നേഹം", "heart": "ഹൃദയം", "sad": "ദു:ഖം"},
    "te": {"love": "ప్రేమ", "heart": "హృదయం", "sad": "దుఃఖం"},
}

def emotional_adaptation(translated_line, source_line, lang_code):
    sentiment = sentiment_analyzer(source_line)[0]
    adapted_line = translated_line
    for eng_word, regional_word in regional_synonyms.get(lang_code, {}).items():
        if eng_word in source_line.lower():
            adapted_line = adapted_line.replace(eng_word, regional_word)
    if sentiment['label'] == 'NEGATIVE':
        adapted_line += " 😔"
    elif sentiment['label'] == 'POSITIVE':
        adapted_line += " ❤️"
    return adapted_line

# 6️⃣ AI-powered Rhyme & Metaphor Engine (enhanced with GPT)
def ai_rhyme_metaphor_engine(target_word, lang_code="ta"):
    prompt = (
        f"Suggest 5 rhyming or metaphorical phrases in {lang_code} that rhyme with '{target_word}' "
        f"and maintain poetic tone and emotion."
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}],
        temperature=0.8,
        max_tokens=150
    )
    suggestions = response['choices'][0]['message']['content'].strip().split('\n')
    suggestions = [s.strip() for s in suggestions if s.strip()]
    return suggestions if suggestions else ["No suggestions found"]

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
    rhythmic_line = rhythmic_adjustment(translated_line, original_syllables, tgt_lang)
    st.subheader("Rhythmic-Aligned Lyric")
    st.write(rhythmic_line)

    # -----------------------
    # Step 3: Pronunciation Guide
    # -----------------------
    st.subheader("Pronunciation Guide")
    audio_file = generate_pronunciation_audio(translated_line, languages[tgt_lang])
    st.audio(audio_file, format="audio/mp3")
    st.write("Play above to hear pronunciation.")

    # -----------------------
    # Step 4: Emotion Adaptation
    # -----------------------
    adapted_line = emotional_adaptation(rhythmic_line, english_lyric, tgt_lang)
    st.subheader("Emotion-Adapted Lyric")
    st.write(adapted_line)

    # -----------------------
    # Step 5: AI Rhyme & Metaphor Suggestions
    # -----------------------
    st.subheader("AI Rhyme & Metaphor Suggestions")
    words = translated_line.strip().split()
    last_word = words[-1].lower()
    rhyme_suggestions = ai_rhyme_metaphor_engine(last_word, tgt_lang)
    st.write(f"Suggested rhymes/metaphors for '{last_word}':")
    for s in rhyme_suggestions:
        st.write("-", s)
