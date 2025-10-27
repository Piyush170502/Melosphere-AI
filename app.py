# app.py
import streamlit as st
import requests
import pronouncing
from deep_translator import GoogleTranslator
import os

# ---------------------------
# Optional: OpenAI imports
# ---------------------------
try:
    from openai import OpenAI
    client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
except ImportError:
    client = None

# ---------------------------
# Translation Function
# ---------------------------
def translate(text, tgt_lang_code):
    try:
        translated = GoogleTranslator(source='auto', target=tgt_lang_code).translate(text)
        return translated
    except Exception as e:
        return f"Error in translation: {e}"

# ---------------------------
# Rhyme Function
# ---------------------------
def get_rhymes(word):
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        rhymes = [item['word'] for item in response.json()]
        return rhymes
    else:
        return []

# ---------------------------
# Syllable Count
# ---------------------------
def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    else:
        return sum(1 for char in word.lower() if char in 'aeiou')

def count_total_syllables(line):
    return sum(count_syllables(w) for w in line.split())

# ---------------------------
# AI-powered Rhythmic Adjustment
# ---------------------------
def rhythmic_adjustment(translated_line, original_syllables, lang_name="Tamil"):
    if not client:
        return translated_line  # fallback if no API key
    prompt = (
        f"Rephrase this {lang_name} lyric to have approximately {original_syllables} syllables, "
        f"keeping meaning, emotion, and rhyme intact: '{translated_line}'"
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content

# ---------------------------
# AI-powered Rhyme & Metaphor Suggestions
# ---------------------------
def suggest_rhymes_metaphors(line, lang_name="Tamil"):
    if not client:
        return []
    prompt = f"Suggest creative rhymes, near-rhymes, and metaphorical expressions in {lang_name} for: '{line}'"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    return response.choices[0].message.content.split('\n')

# ---------------------------
# Pronunciation Guide
# ---------------------------
def pronunciation_guide(word, lang_name="Tamil"):
    # Using Google Transliteration API or simple phonetic approximation
    # Here we provide fallback using deep_translator (basic)
    try:
        phonetic = GoogleTranslator(source='auto', target='en').translate(word)
        return phonetic
    except:
        return word

# ---------------------------
# Streamlit App
# ---------------------------
def main():
    st.title("🎵 Melosphere AI - Lyrics without limits")
    
    # User input
    lyric_input = st.text_area("Enter English lyric(s) or lines:", height=150)
    
    languages = {
        "Tamil": "ta",
        "Hindi": "hi",
        "Kannada": "kn",
        "Telugu": "te",
        "Malayalam": "ml",
        "Spanish": "es",
        "Japanese": "ja",
    }
    tgt_lang_name = st.selectbox("Select target language:", list(languages.keys()))
    tgt_lang_code = languages[tgt_lang_name]
    
    if lyric_input:
        st.subheader("Original English Lyric")
        st.write(lyric_input)
        
        # ---------------------------
        # Translate
        # ---------------------------
        translated_line = translate(lyric_input, tgt_lang_code)
        st.subheader(f"Translated ({tgt_lang_name}) Lyric")
        st.write(translated_line)
        
        # ---------------------------
        # Syllable & Rhythm
        # ---------------------------
        total_syllables = count_total_syllables(lyric_input)
        rhythmic_line = rhythmic_adjustment(translated_line, total_syllables, tgt_lang_name)
        st.subheader("Rhythmic-Aligned Lyric")
        st.write(rhythmic_line)
        
        # ---------------------------
        # Rhymes & Metaphors
        # ---------------------------
        st.subheader("Creative Rhyme & Metaphor Suggestions")
        suggestions = suggest_rhymes_metaphors(rhythmic_line, tgt_lang_name)
        if suggestions:
            for s in suggestions:
                st.write("-", s)
        else:
            st.write("No suggestions (API key may be missing).")
        
        # ---------------------------
        # Pronunciation Guide
        # ---------------------------
        st.subheader("Pronunciation Guide")
        words = rhythmic_line.split()
        pronun_dict = {w: pronunciation_guide(w, tgt_lang_name) for w in words}
        st.write(pronun_dict)
        
        # ---------------------------
        # Rhymes for last word
        # ---------------------------
        last_word = words[-1]
        rhymes = get_rhymes(last_word)
        st.subheader(f"Rhymes for '{last_word}'")
        if rhymes:
            st.write(", ".join(rhymes))
        else:
            st.write("No rhymes found.")

if __name__ == "__main__":
    main()
