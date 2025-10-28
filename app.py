import streamlit as st
import requests
import pronouncing
import os

# ========================
# Google Translation API
# ========================

def translate_text(text, target_lang):
    api_key = st.secrets["general"]["GOOGLE_TRANSLATE_API_KEY"]
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {
        "q": text,
        "target": target_lang,
        "format": "text"
    }

    try:
        response = requests.post(url, json=payload)
        data = response.json()
        if "data" in data and "translations" in data["data"]:
            return data["data"]["translations"][0]["translatedText"]
        else:
            return f"Error: {data}"
    except Exception as e:
        return f"Error during translation: {e}"

# ========================
# Rhyming and Syllables
# ========================

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
        return sum(1 for char in word.lower() if char in 'aeiou')

# ========================
# Streamlit App
# ========================

def main():
    st.title("🎵 Melosphere AI - Lyrics Without Limits")

    lyric_line = st.text_input("Enter your Lyric Line (English):")

    languages = {
        "Spanish": "es",
        "Kannada": "kn",
        "Tamil": "ta",
        "Malayalam": "ml",
        "Hindi": "hi",
        "Telugu": "te",
        "Japanese": "ja",
    }

    tgt_lang = st.selectbox("Select target language for translation:", list(languages.keys()))

    if lyric_line:
        words = lyric_line.strip().split()
        last_word = words[-1].lower()

        rhymes = get_rhymes(last_word)
        if rhymes:
            st.write(f"**Rhymes for '{last_word}':** {', '.join(rhymes)}")
        else:
            st.write(f"No rhymes found for '{last_word}'.")

        syllables_per_word = {w: count_syllables(w) for w in words}
        total_syllables = sum(syllables_per_word.values())
        st.write(f"**Syllables per word:** {syllables_per_word}")
        st.write(f"**Total syllables:** {total_syllables}")

        translation = translate_text(lyric_line, languages[tgt_lang])
        st.write(f"**{tgt_lang} Translation:** {translation}")

if __name__ == "__main__":
    main()
