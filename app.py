import streamlit as st
import requests
from deep_translator import GoogleTranslator
import pronouncing
import re
import random
import time

# -----------------------------
# TRANSLATION UTILITIES
# -----------------------------
def translate(text, tgt_lang_code, retries=2):
    """Translate text safely, fallback to original if error."""
    if not text or not isinstance(text, str):
        return ""
    try:
        if tgt_lang_code == "en":
            return text
        result = GoogleTranslator(source="auto", target=tgt_lang_code).translate(text)
        if result is None or not isinstance(result, str):
            raise ValueError("Empty translation result")
        return result
    except Exception:
        if retries > 0:
            time.sleep(0.5)
            return translate(text, tgt_lang_code, retries - 1)
        return text  # fallback to original text

def clean_blended_line(line):
    """Fix spacing, punctuation, and capitalization."""
    if not line:
        return ""
    line = re.sub(r"\s+([.,!?])", r"\1", line)
    line = re.sub(r"\s+", " ", line).strip()
    return line[0].upper() + line[1:] if line else line


def smart_phrase_split(line):
    """Split text into small phrases (2–5 words each)."""
    words = line.split()
    phrases = []
    current = []
    for w in words:
        current.append(w)
        if len(current) >= random.randint(2, 5) or w.endswith(('.', ',', ';', '?', '!')):
            phrases.append(" ".join(current))
            current = []
    if current:
        phrases.append(" ".join(current))
    return phrases


def translate_polyglot_line(line, target_languages, creativity=0.5):
    """
    Smarter phrase-level multilingual blending.
    - Keeps small English anchors.
    - Translates in 2–5 word phrases.
    - Ensures smoother, more musical flow.
    """
    if not line:
        return ""

    anchor_words = {"you", "i", "my", "me", "and", "the", "your", "a", "to", "for", "of", "in"}
    phrases = smart_phrase_split(line)
    blended_phrases = []

    for phrase in phrases:
        # Check if this phrase contains mostly anchors → keep English
        words = phrase.lower().split()
        if any(w in anchor_words for w in words) and random.random() > creativity * 0.7:
            tgt_lang = "en"
        else:
            if random.random() < creativity:
                tgt_lang = random.choice(target_languages)
            else:
                tgt_lang = "en"

        translated = translate(phrase, tgt_lang)
        blended_phrases.append(translated if translated else phrase)

    blended_line = " ".join(blended_phrases)
    return clean_blended_line(blended_line)

# -----------------------------
# RHYME & SYLLABLE UTILITIES
# -----------------------------
def get_rhymes(word):
    try:
        response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
        if response.status_code == 200:
            return [item["word"] for item in response.json()]
        return []
    except:
        return []

def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for c in word.lower() if c in "aeiou")

# -----------------------------
# STREAMLIT APP
# -----------------------------
def main():
    st.set_page_config(page_title="Melosphere AI", page_icon="🎶")
    st.title("🎵 Melosphere AI — Lyrics Without Limits 🌍")

    st.markdown("""
    **Your all-in-one creative co-writer, translator, and vocal coach.**  
    Empowering lyricists to create multilingual songs while preserving rhythm, rhyme, and emotion.
    """)

    st.divider()
    st.header("Phase 1 — Multilingual Translation & Rhyme Assistant")

    lyric_line = st.text_input("🎤 Enter your lyric line (English):")

    languages = {
        "English": "en",
        "Spanish": "es",
        "Kannada": "kn",
        "Tamil": "ta",
        "Malayalam": "ml",
        "Hindi": "hi",
        "Telugu": "te",
        "Japanese": "ja",
        "French": "fr",
        "German": "de",
    }

    tgt_lang = st.selectbox("🌐 Select target language for translation:", list(languages.keys()))

    if lyric_line:
        words = lyric_line.strip().split()
        last_word = words[-1].lower()

        # Rhyme suggestions
        rhymes = get_rhymes(last_word)
        if rhymes:
            st.write(f"**Rhymes for '{last_word}':** {', '.join(rhymes)}")
        else:
            st.write(f"No rhymes found for '{last_word}'.")

        # Syllable count
        syllables = {w: count_syllables(w) for w in words}
        st.write("🪶 **Syllables per word:**", syllables)
        st.write("🔢 **Total syllables:**", sum(syllables.values()))

        # Translation
        translated = translate(lyric_line, languages[tgt_lang])
        st.success(f"**{tgt_lang} Translation:** {translated}")

    # -----------------------------
    # PHASE 2 — POLYGLOT LYRIC BLENDING
    # -----------------------------
    st.divider()
    st.header("Phase 2 — Polyglot Lyric Blending 🌐")

    blended_langs = st.multiselect(
        "Select languages to blend (include English for smoother results):",
        list(languages.keys()),
        default=["English", "Spanish", "Hindi", "Tamil"]
    )

    creativity = st.slider(
        "🎨 Creativity Level (0 = Mostly English, 1 = Full Multilingual Remix)",
        0.0, 1.0, 0.6, 0.1
    )

    if lyric_line and blended_langs:
        codes = [languages[l] for l in blended_langs]
        blended = translate_polyglot_line(lyric_line, codes, creativity)
        st.write("### 🎶 **Blended Lyric Line:**")
        st.success(blended)

        st.caption("💡 Tip: Higher creativity gives richer multilingual texture, but lower values keep phrasing smoother.")

    st.divider()
    st.markdown("""
    🚀 **Next Phases Preview**
    - **Phase 3:** Rhythmic Translation Enhancements  
    - **Phase 4:** Pronunciation Guide & Emotion Adaptation  
    - **Phase 5:** AI Rhyme–Metaphor Engine + DAW Integration  
    """)

if __name__ == "__main__":
    main()
