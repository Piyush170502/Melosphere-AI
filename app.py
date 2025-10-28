import streamlit as st
import requests
import pronouncing
import math
import difflib

# ------------------------
# Google Translation Helper
# ------------------------

def translate_text(text, target_lang):
    api_key = st.secrets.get("general", {}).get("GOOGLE_TRANSLATE_API_KEY", None)
    if not api_key:
        return "⚠️ Translation API key not found in Streamlit secrets."
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {"q": text, "target": target_lang, "format": "text"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if "data" in data and "translations" in data["data"]:
            return data["data"]["translations"][0]["translatedText"]
        elif "error" in data:
            return f"API error: {data['error'].get('message','unknown')}"
    except Exception as e:
        return f"Error during translation: {e}"

# ------------------------
# Syllable Counting
# ------------------------

def count_syllables_english(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for ch in word.lower() if ch in 'aeiou')

def count_syllables_heuristic(text):
    text = str(text)
    for ch in ",.!?;:-—()\"'":
        text = text.replace(ch, " ")
    words = [w for w in text.split() if w.strip()]
    syllables = 0
    for w in words:
        lw = w.lower()
        groups = 0
        prev_vowel = False
        for ch in lw:
            is_v = ch in "aeiouáàâäãåāéèêëēíìîïīóòôöõōúùûüūy"
            if is_v and not prev_vowel:
                groups += 1
            prev_vowel = is_v
        if groups == 0:
            groups = 1
        syllables += groups
    return syllables

def count_syllables_general(text, lang_code):
    if not text or not isinstance(text, str):
        return 0
    if lang_code.startswith("en"):
        words = [w for w in text.split() if w.strip()]
        return sum(count_syllables_english(w) for w in words)
    else:
        return count_syllables_heuristic(text)

# ------------------------
# Rhythm Adjustment Logic
# ------------------------

def adjust_translation_rhythm(original, translated, lang_code):
    """
    Adjust translation roughly to match syllable count of original line.
    Adds or trims filler words if the difference is large.
    """
    orig_syll = count_syllables_general(original, "en")
    trans_syll = count_syllables_general(translated, lang_code)
    diff = trans_syll - orig_syll

    if abs(diff) <= 1:
        return translated  # good rhythm match

    words = translated.split()
    if diff > 1:
        # Too long → remove least-important words
        trimmed = " ".join(words[:-abs(diff)]) if len(words) > abs(diff) else translated
        return trimmed
    else:
        # Too short → duplicate last word to stretch rhythm
        last = words[-1] if words else ""
        extended = translated + " " + (" ".join([last] * abs(diff)))
        return extended

# ------------------------
# Streamlit UI
# ------------------------

def main():
    st.set_page_config(page_title="Melosphere — Rhythmic Translation Enhancer", layout="wide")
    st.title("🎶 Melosphere — Phase 2: Rhythmic Translation Enhancements")

    st.markdown(
        """
        This tool preserves the *musicality* of your lyrics by ensuring the translated version roughly matches the
        **syllable count, stress pattern, and rhythm** of the original line.
        """
    )

    # Input
    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("🎵 Enter your lyric line (English):", height=80)
    with col2:
        available_languages = {
            "Spanish": "es",
            "Kannada": "kn",
            "Tamil": "ta",
            "Malayalam": "ml",
            "Hindi": "hi",
            "Telugu": "te",
            "Japanese": "ja",
            "French": "fr",
            "Portuguese": "pt",
            "German": "de",
            "Korean": "ko",
        }
        selected = st.selectbox("🎯 Target language:", options=list(available_languages.keys()), index=0)
        show_syllables = st.checkbox("Show rhythm analysis details", value=True)

    if not lyric_line:
        st.info("Enter a lyric line above to generate rhythmic translations.")
        return

    target_code = available_languages[selected]

    # Translate
    with st.spinner("Translating..."):
        translation = translate_text(lyric_line, target_code)

    # Adjust for rhythm
    adjusted = adjust_translation_rhythm(lyric_line, translation, target_code)

    # Display
    st.subheader("Original")
    st.write(lyric_line)
    st.caption(f"Syllables: {count_syllables_general(lyric_line, 'en')}")

    st.subheader(f"Translated ({selected})")
    st.write(translation)
    st.caption(f"Syllables: {count_syllables_general(translation, target_code)}")

    st.subheader("🎼 Rhythm-Adjusted Translation")
    st.success(adjusted)
    st.caption(f"Syllables: {count_syllables_general(adjusted, target_code)}")

    # Details
    if show_syllables:
        st.markdown("---")
        st.subheader("Rhythmic Alignment")
        orig_syll = count_syllables_general(lyric_line, "en")
        trans_syll = count_syllables_general(translation, target_code)
        diff = trans_syll - orig_syll
        if abs(diff) <= 1:
            st.success(f"✅ Perfect rhythm alignment ({orig_syll} vs {trans_syll} syllables)")
        elif abs(diff) <= 3:
            st.warning(f"⚠️ Slight rhythm deviation ({orig_syll} vs {trans_syll} syllables)")
        else:
            st.error(f"❌ Large rhythm mismatch ({orig_syll} vs {trans_syll} syllables)")

    # Export
    st.markdown("---")
    st.subheader("Export")
    st.code(adjusted, language="text")
    st.download_button("Download adjusted lyric", adjusted, file_name="melosphere_rhythmic_translation.txt")

    st.markdown(
        """
        **Notes:**
        - This module currently performs basic rhythm alignment by syllable count.
        - Future updates will include stress pattern modeling and beat-matching to melody lines.
        """
    )


if __name__ == "__main__":
    main()
