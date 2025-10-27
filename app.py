# app.py
import streamlit as st
import requests
from deep_translator import GoogleTranslator
from indicnlp.tokenize import indic_tokenize
from indicnlp import common, transliterate
import pronouncing
import re

# Initialize Indic NLP
INDIC_NLP_RESOURCES = "./indic_nlp_resources"
common.set_resources_path(INDIC_NLP_RESOURCES)

# ----------- FUNCTIONS -----------

# Translation using Google Translator
def translate(text, tgt_lang_code):
    try:
        return GoogleTranslator(source='auto', target=tgt_lang_code).translate(text)
    except Exception as e:
        return f"Error in translation: {e}"

# English rhymes using Datamuse API
def get_rhymes_en(word):
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        return [item['word'] for item in response.json()]
    return []

# Indian language rhyme suggestions (crude, by last vowel sound)
def get_rhymes_indic(word):
    vowels = 'अआइईउऊएऐओऔािीुूेैोौ'
    last_vowel_match = re.findall(f"[{vowels}]", word)
    if not last_vowel_match:
        return []
    last_vowel = last_vowel_match[-1]
    # For demo: return other words with same last vowel from a small sample dictionary
    sample_dict = ["सपना", "ख़्वाब", "मन", "जन", "गगन", "अमन", "धरम", "कम"]
    rhymes = [w for w in sample_dict if last_vowel in w]
    return rhymes

# English syllable counting
def count_syllables_en(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    else:
        # fallback: count vowels
        return sum(1 for char in word.lower() if char in 'aeiou')

# Indic language syllable counting (approximation)
def count_syllables_indic(line, lang_code):
    tokens = indic_tokenize.trivial_tokenize(line)
    vowels = 'अआइईउऊएऐओऔािीुूेैोौ'  # Hindi/Tamil approximation
    total = 0
    for tok in tokens:
        total += sum(1 for char in tok if char in vowels)
    return total

# Rhythmic adjustment
def rhythmic_adjustment(translated_line, original_syllables, lang_code):
    translated_syllables = count_syllables_indic(translated_line, lang_code)
    diff = original_syllables - translated_syllables
    if diff > 0:
        translated_line += " …" * diff
    elif diff < 0:
        translated_line = translated_line[:diff]  # crude trimming
    return translated_line

# Emotion detection (English)
positive_words = ["love", "happy", "joy", "smile", "delight"]
negative_words = ["sad", "pain", "cry", "hate", "heartbreak"]

def detect_emotion_en(text):
    text = text.lower()
    pos = sum(text.count(w) for w in positive_words)
    neg = sum(text.count(w) for w in negative_words)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"

# Emotion-aware translation adjustment
def adjust_emotion(translated_line, emotion, lang_code):
    if emotion == "positive":
        return translated_line + " 😊"
    elif emotion == "negative":
        return translated_line + " 😢"
    return translated_line

# ----------- STREAMLIT APP -----------

st.title("Melosphere AI - Enhanced Open Source Lyric Translator")

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

    # 4. Rhyme suggestions
    last_word_en = lyric_input.strip().split()[-1].lower()
    st.subheader(f"Rhyme Suggestions for '{last_word_en}'")
    if tgt_lang == "English":
        rhymes = get_rhymes_en(last_word_en)
    else:
        # crude: use last word of translated line
        last_word_indic = translated_line.strip().split()[-1]
        rhymes = get_rhymes_indic(last_word_indic)
    if rhymes:
        st.write(", ".join(rhymes))
    else:
        st.write("No rhymes found.")

    # 5. Emotion adjustment
    final_line = adjust_emotion(rhythmic_line, emotion, languages[tgt_lang])
    st.subheader("Final Lyric with Emotion Adjustment")
    st.write(final_line)
