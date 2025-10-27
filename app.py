import streamlit as st
import requests
import pronouncing
import random
import re
from transformers import MarianMTModel, MarianTokenizer

# -----------------------------
# MarianMT Models Setup
# -----------------------------
model_names = {
    'hi': 'Helsinki-NLP/opus-mt-en-hi',
    'ta': 'Helsinki-NLP/opus-mt-en-ta',
    'te': 'Helsinki-NLP/opus-mt-en-te',
    'ml': 'Helsinki-NLP/opus-mt-en-ml',
    'ja': 'Helsinki-NLP/opus-mt-en-ja'  # Japanese
}

st.info("Loading translation models... this may take a minute on first run.")

models = {lang: MarianMTModel.from_pretrained(model_names[lang]) for lang in model_names}
tokenizers = {lang: MarianTokenizer.from_pretrained(model_names[lang]) for lang in model_names}

# -----------------------------
# Helper Functions
# -----------------------------
def translate(text, tgt_lang):
    if tgt_lang == 'en':
        return text
    tokenizer = tokenizers[tgt_lang]
    model = models[tgt_lang]
    tokenizer.src_lang = 'en_XX'
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    translated_tokens = model.generate(**inputs)
    return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)

def get_rhymes(word):
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        return [item['word'] for item in response.json()]
    return []

def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    else:
        return sum(1 for char in word.lower() if char in 'aeiou')

def polyglot_blend(text, tgt_langs, creativity=0.5):
    sentences = re.split(r'([.?!])', text)
    blended = []

    for i in range(0, len(sentences), 2):
        sentence = sentences[i].strip()
        if not sentence:
            continue
        punct = sentences[i + 1] if i + 1 < len(sentences) else ""

        # Decide whether to translate this chunk
        if tgt_langs and random.random() < creativity:
            tgt = random.choice(tgt_langs)
        else:
            tgt = 'en'

        translated = translate(sentence, tgt)
        blended.append(translated + punct)

    return re.sub(r'\s+([.,!?])', r'\1', " ".join(blended)).strip()

# -----------------------------
# Streamlit App
# -----------------------------
st.title("Melosphere AI - Polyglot Lyric Blending")

lyric_line = st.text_area("Enter your Lyric Line (English):", height=100)

languages = {
    "English": "en",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Japanese": "ja",
}

blended_langs = st.multiselect(
    "Select target languages for blending:",
    list(languages.keys())[1:],  # skip English
    default=["Hindi", "Tamil"]
)

creativity = st.slider("Blending Creativity", 0.0, 1.0, 0.5)

if lyric_line and blended_langs:
    tgt_codes = [languages[l] for l in blended_langs]
    blended = polyglot_blend(lyric_line, tgt_codes, creativity)
    st.write("### **Blended Lyric Line:**")
    st.success(blended)

# -----------------------------
# Rhyme and Syllable Support
# -----------------------------
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
