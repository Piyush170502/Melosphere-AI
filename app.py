import streamlit as st
from googletrans import Translator
import re

translator = Translator()

# -------------------------------
# Utility Functions
# -------------------------------
def count_syllables_general(text, lang):
    """Approximate syllable counter based on vowel clusters."""
    text = text.lower()
    # Basic vowel group match per language
    if lang in ["ja", "zh"]:
        # Asian languages (treat each character as a syllable approximation)
        return len(text)
    elif lang in ["hi", "ta"]:
        # Indic scripts: rough vowel-based estimation
        vowels = "अआइईउऊएऐओऔािीुूेैोौंः"
        return len([c for c in text if c in vowels])
    else:
        # Latin scripts
        return len(re.findall(r"[aeiouy]+", text))

def remove_duplicates(text):
    """Simple duplicate word removal."""
    words = text.split()
    seen = set()
    deduped = []
    for w in words:
        if w.lower() not in seen:
            seen.add(w.lower())
            deduped.append(w)
    return " ".join(deduped)

def interleave_words(lang1_text, lang2_text):
    """Alternate words from two languages."""
    l1_words = lang1_text.split()
    l2_words = lang2_text.split()
    blended = []
    for i in range(max(len(l1_words), len(l2_words))):
        if i < len(l1_words):
            blended.append(l1_words[i])
        if i < len(l2_words):
            blended.append(l2_words[i])
    return " ".join(blended)

def phrase_swap(lang1_text, lang2_text):
    """Swap short phrases between two language lines."""
    l1_phrases = re.split(r"[,.;:!?]", lang1_text)
    l2_phrases = re.split(r"[,.;:!?]", lang2_text)
    blended = []
    for i in range(max(len(l1_phrases), len(l2_phrases))):
        if i < len(l1_phrases):
            blended.append(l1_phrases[i].strip())
        if i < len(l2_phrases):
            blended.append(l2_phrases[i].strip())
    return " / ".join([p for p in blended if p])

def last_word_swap(lang1_text, lang2_text):
    """Swap last words between languages."""
    l1_words = lang1_text.split()
    l2_words = lang2_text.split()
    if not l1_words or not l2_words:
        return lang1_text + " / " + lang2_text
    l1_words[-1], l2_words[-1] = l2_words[-1], l1_words[-1]
    return " ".join(l1_words) + " / " + " ".join(l2_words)

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="Polyglot Lyrics Studio", layout="wide")

st.title("🎶 Polyglot Lyrics Studio")
st.caption("Multilingual lyric translation, blending, rhythmic alignment & phonetic guidance.")

# Phase 1: Input
lyric_line = st.text_input("Enter an English lyric line:")
available_languages = {
    "Hindi": "hi",
    "Tamil": "ta",
    "Japanese": "ja",
    "Spanish": "es",
    "French": "fr",
    "Chinese": "zh-cn",
}
selected = st.multiselect("Select target languages:", available_languages.keys())

# Phase 2: Translation + Polyglot Blending
if lyric_line and selected:
    st.subheader("🌍 Translations")
    translations = {}

    for lang_name in selected:
        code = available_languages[lang_name]
        try:
            translated = translator.translate(lyric_line, src="en", dest=code).text
        except Exception:
            translated = "(Translation failed)"
        translations[lang_name] = translated
        st.write(f"**{lang_name}:** {translated}")

    st.divider()
    st.subheader("🧬 Polyglot Blending")

    col1, col2 = st.columns(2)
    with col1:
        blend_mode = st.selectbox(
            "Blending Mode",
            ["Interleave Words", "Phrase Swap", "Last Word Swap"]
        )
    with col2:
        deduplicate = st.checkbox("🔁 Remove Duplicates", value=True)

    if len(selected) == 2:
        lang1, lang2 = selected
        text1, text2 = translations[lang1], translations[lang2]

        if blend_mode == "Interleave Words":
            blended = interleave_words(text1, text2)
        elif blend_mode == "Phrase Swap":
            blended = phrase_swap(text1, text2)
        else:
            blended = last_word_swap(text1, text2)

        if deduplicate:
            blended = remove_duplicates(blended)

        st.success(f"**Blended ({lang1} + {lang2}):** {blended}")
    elif len(selected) != 2:
        st.info("ℹ️ Polyglot blending works best when exactly two languages are selected.")

    st.divider()

    # -------------------------------
    # Syllable Analysis
    # -------------------------------
    st.subheader("🔠 Syllable Analysis")
    show_syllables = st.checkbox("Show syllable counts", value=True)

    if show_syllables:
        syllables_en = count_syllables_general(lyric_line, "en")
        st.write(f"**English:** {syllables_en} syllables")

        for lang_name in selected:
            code = available_languages[lang_name]
            trans_text = translations[lang_name]
            syllables = count_syllables_general(trans_text, code)
            st.write(f"**{lang_name}:** {syllables} syllables")

        st.info("Helps you adjust lyrics to keep similar syllable counts for musical rhythm.")

    # --------------------------------------------------
    # 🎵 Rhythmic Translation Enhancements
    # --------------------------------------------------
    rhythmic_mode = st.checkbox("Enable Rhythmic Translation Enhancements (Experimental)", value=False)

    if rhythmic_mode and show_syllables:
        st.subheader("🎵 Rhythmic Alignment Analysis")

        def rhythm_bar(count, target_count):
            symbol = "●"
            return " ".join([symbol] * count) if count > 0 else "–"

        source_syll = count_syllables_general(lyric_line, "en")

        st.write(f"**Source rhythm ({source_syll} syllables):**")
        st.code(rhythm_bar(source_syll, source_syll))

        for lang_name in selected:
            code = available_languages[lang_name]
            trans_text = translations[lang_name]
            syllables = count_syllables_general(trans_text, code)
            diff = syllables - source_syll

            # Color-coded rhythm feedback
            color = "green" if diff == 0 else "orange" if abs(diff) <= 2 else "red"
            st.markdown(
                f"""
                <div style="margin-bottom:10px">
                    <b style="color:{color}">{lang_name} ({syllables} syllables):</b><br>
                    <code>{rhythm_bar(syllables, source_syll)}</code><br>
                    {"✅ Perfect match" if diff==0 else "🟡 Near match" if abs(diff)<=2 else "🔴 Off-beat – consider editing translation"}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.info("These rhythm bars help visualize syllable alignment — aim for near or perfect matches for singable translations.")
