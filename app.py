import streamlit as st
import requests
import pronouncing
from transformers import MarianMTModel, MarianTokenizer

# Cache model loading to speed up app start
@st.cache_resource
def load_translation_model(src_lang='en', tgt_lang='es'):
    model_name = f'Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}'
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    return tokenizer, model

tokenizer, model = load_translation_model()

def translate(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True)
    translated = model.generate(**inputs)
    tgt_text = [tokenizer.decode(t, skip_special_tokens=True) for t in translated]
    return tgt_text[0]

def get_rhymes(word):
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        rhymes = [item['word'] for item in response.json()]
        return rhymes
    else:
        return []

 
def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    else:
        # Fallback heuristic: count vowels as syllables
        return sum(1 for char in word.lower() if char in 'aeiou')

def main():
    st.title("Melosphere AI - Lyric Assistant Prototype")

    lyric_line = st.text_input("Enter your lyric line (English):")

    if lyric_line:
        words = lyric_line.strip().split()
        last_word = words[-1].lower()

        # Rhymes for the last word
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
