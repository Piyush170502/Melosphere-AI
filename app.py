# app.py
import streamlit as st
import requests
from deep_translator import GoogleTranslator
from indicnlp.tokenize import indic_tokenize
from indicnlp import common
from indicnlp import transliterate
from indicnlp.morph import unsup_morph
import pronouncing

# Initialize Indic NLP
INDIC_NLP_RESOURCES = "./indic_nlp_resources"
common.set_resources_path(INDIC_NLP_RESOURCES)

# ----------- FUNCTIONS -----------

# Translation using Google Translator
def translate(text, tgt_lang_code):
    try:
        translated = GoogleTranslator(source='auto', target=tgt_lang_code).translate(text)
        return translated
    except Exception as e:
        return f"Error in translation: {e}"

# English rhymes using Datamuse API
def get_rhymes(word):
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        rhymes = [item['word'] for item in response.json()]
        return rhymes
    return []

# English syllable counting
def count_syllables_en(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    else:
        return sum(1 for char in word.lower() if char in 'aeiou')

# Indic language syllable counting (approximation)
def count_syllables_indic(line, lang_code):
    tokens = indic_tokenize.trivial_tokenize(line)
    vowels = 'अआइईउऊएऐओऔािीुूेैोौ'  # basic Hindi/Tamil vowels
    total = 0
    for tok in tokens:
        total += sum(1 for char in tok if char in vowels)
    return total

# Rhythmic adjustment (simple substitution to match syllables)
def rhythmic_adjustment(translated_line, original_syllables, lang_code):
    translated_syllables = count_syllables_indic(translated_line, lang_code)
    diff = original_syllables - translated_syllables
    if diff > 0:
        translated_line += " …" * diff
    elif diff < 0:
        translated_line = translated_line[:diff]  # crude trimming
    return translated_line

# Simple emotion detection using word lists
positive_words = ["love", "happy", "joy", "smile"]
negative_words = ["sad", "pain", "cry", "hate"]

def detect_emotion_en(text):
    text = text.lower()
    pos = sum(text.count(w) for w in positive_words)
    neg = sum(text.count(w) for w in negative_words)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"

def adjust_emotion(translated_line, emotion, lang_code):
    # For demo: append emoji or simple words
    if emotion == "positive":
        return translated_line + " 😊"
    elif emotion == "negative":
        return translated_line + " 😢"
    return translated_line

# ----------- STREAMLIT APP -----------

st.title("Melosphere AI - Open Source Lyric Translator")

lyric_input = st.text_area("Enter your English lyric line or verse:")

languages = {
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Kannada": "kn",
}

tgt_lang = st.selectbox("Select target language:", list(languages.keys()))

if lyric_input:
    # 1. Emotion detection
    emotion = detect_emotion_en(lyric_input)
    st.write(f"Detected Emotion: {emotion}")

    # 2. Translation
    translated_line = translate(lyric_input, languages[tgt_lang])
    st.subheader(f"{tgt_lang} Translation")
    st.write(translated_line)

    # 3. Rhythmic adjustment
    original_syllables = sum(count_syllables_en(w) for w in lyric_input.split())
    rhythmic_line = rhythmic_adjustment(translated_line, original_syllables, languages[tgt_lang])
    st.subheader("Rhythmic-Aligned Lyric")
    st.write(rhythmic_line)

    # 4. Rhyme suggestions (last English word)
    last_word = lyric_input.strip().split()[-1].lower()
    rhymes = get_rhymes(last_word)
    st.subheader(f"Rhymes for '{last_word}'")
    if rhymes:
        st.write(", ".join(rhymes))
    else:
        st.write("No rhymes found.")

    # 5. Emotion adjustment
    final_line = adjust_emotion(rhythmic_line, emotion, languages[tgt_lang])
    st.subheader("Final Lyric with Emotion Adjustment")
    st.write(final_line)
