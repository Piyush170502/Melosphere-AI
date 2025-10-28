import streamlit as st
import requests
import pronouncing
import random

# ========================
# Google Translation API
# ========================

def translate_text(text, target_lang):
    api_key = st.secrets["general"]["GOOGLE_TRANSLATE_API_KEY"]
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {"q": text, "target": target_lang, "format": "text"}

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
# Polyglot Blending Logic
# ========================

def blend_lyrics(text1, text2, mode="Interleave"):
    words1 = text1.split()
    words2 = text2.split()

    if mode == "Interleave":
        # Alternate between words from both languages
        blended = []
        for i in range(max(len(words1), len(words2))):
            if i < len(words1): blended.append(words1[i])
            if i < len(words2): blended.append(words2[i])
        return " ".join(blended)

    elif mode == "Phrase Swap":
        half1 = len(words1) // 2
        half2 = len(words2) // 2
        return " ".join(words1[:half1] + words2[half2:])

    elif mode == "Last Word Swap":
        if len(words1) > 0 and len(words2) > 0:
            return " ".join(words1[:-1] + [words2[-1]])
        return text1

    else:
        return text1

# ========================
# Streamlit App
# ========================

def main():
    st.title("🎵 Melosphere AI - Multilingual Lyric Blending")

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

    col1, col2 = st.columns(2)
    with col1:
        lang1 = st.selectbox("Select Language 1:", list(languages.keys()), index=0)
    with col2:
        lang2 = st.selectbox("Select Language 2:", list(languages.keys()), index=1)

    mode = st.selectbox("Select Blending Mode:", ["Interleave", "Phrase Swap", "Last Word Swap"])
    remove_duplicates = st.checkbox("🧹 Remove duplicate words/phrases", value=False)

    if lyric_line and st.button("✨ Generate Blend"):
        # Translation
        trans1 = translate_text(lyric_line, languages[lang1])
        trans2 = translate_text(lyric_line, languages[lang2])

        st.write(f"**{lang1} Translation:** {trans1}")
        st.write(f"**{lang2} Translation:** {trans2}")

        # Blend
        blended_line = blend_lyrics(trans1, trans2, mode)

        # Optional Deduplication
        if remove_duplicates:
            words = blended_line.split()
            deduped = [words[0]]
            for w in words[1:]:
                if w != deduped[-1]:
                    deduped.append(w)
            blended_line = " ".join(deduped)

        st.subheader("🎤 Blended Output")
        st.write(blended_line)

        # Rhythm check (optional visual feedback)
        syllables_src = sum(count_syllables(w) for w in lyric_line.split())
        syllables_blend = sum(count_syllables(w) for w in blended_line.split())
        diff = abs(syllables_src - syllables_blend)

        if diff == 0:
            st.success("✅ Rhythm match perfect!")
        elif diff <= 2:
            st.warning(f"⚠️ Rhythm near match ({diff} syllable difference).")
        else:
            st.error(f"❌ Rhythm mismatch ({diff} syllables off). Try adjusting wording.")

if __name__ == "__main__":
    main()
