import streamlit as st
import requests
import pronouncing

# -----------------------------
# Load Google API Key from Streamlit Secrets
# -----------------------------
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# -----------------------------
# Languages
# -----------------------------
languages = {
    "English": "en",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Japanese": "ja"
}

# -----------------------------
# Google Translate API function
# -----------------------------
def translate_text(text, target_lang):
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {
        "q": text,
        "target": target_lang,
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()['data']['translations'][0]['translatedText']
    else:
        return f"Error: {response.text}"

# -----------------------------
# Get rhymes for a word
# -----------------------------
def get_rhymes(word):
    response = requests.get(f"https://api.datamuse.com/words?rel_rhy={word}&max=10")
    if response.status_code == 200:
        rhymes = [item['word'] for item in response.json()]
        return rhymes
    else:
        return []

# -----------------------------
# Count syllables
# -----------------------------
def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    else:
        # Fallback: approximate by counting vowels
        return sum(1 for char in word.lower() if char in 'aeiou')

# -----------------------------
# Polygot lyric blending
# -----------------------------
def translate_polyglot_line(text, selected_langs):
    words = text.strip().split()
    blended_words = []
    n_langs = len(selected_langs)
    for i, word in enumerate(words):
        # Cycle through selected languages
        lang = selected_langs[i % n_langs]
        if lang == "en":
            blended_words.append(word)
        else:
            translated = translate_text(word, lang)
            blended_words.append(translated)
    return " ".join(blended_words)

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🎵 Melosphere AI - Polygot Lyric Creator")

lyric_line = st.text_input("Enter your Lyric Line (English):")

# Multi-select for blending
blended_langs = st.multiselect(
    "Select languages for blending (English included for smoothness):",
    options=list(languages.keys()),
    default=["English", "Hindi", "Tamil"]
)

if lyric_line and blended_langs:
    selected_codes = [languages[l] for l in blended_langs]
    blended = translate_polyglot_line(lyric_line, selected_codes)
    st.write("### **Blended Lyric Line:**")
    st.success(blended)

    # Rhymes for last word
    last_word = lyric_line.strip().split()[-1].lower()
    rhymes = get_rhymes(last_word)
    if rhymes:
        st.write(f"**Rhymes for '{last_word}':** {', '.join(rhymes)}")
    else:
        st.write(f"No rhymes found for '{last_word}'.")

    # Syllable count
    syllables_per_word = {w: count_syllables(w) for w in lyric_line.strip().split()}
    total_syllables = sum(syllables_per_word.values())
    st.write(f"**Syllables per word:** {syllables_per_word}")
    st.write(f"**Total syllables:** {total_syllables}")
