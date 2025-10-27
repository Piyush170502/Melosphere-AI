import streamlit as st
import requests
import pronouncing
from deep_translator import GoogleTranslator

# =========================
# TRANSLATION FUNCTION
# =========================
@st.cache_data(ttl=3600)
def translate_cached(text, tgt_lang_code):
    """
    Translates text using GoogleTranslator (Deep Translator wrapper) with caching for performance.
    """
    try:
        return GoogleTranslator(source='auto', target=tgt_lang_code).translate(text)
    except Exception as e:
        return f"Error in translation: {e}"

# =========================
# RHYME + RHYTHM FUNCTIONS
# =========================
@st.cache_data(ttl=3600)
def get_rhymes_cached(word):
    """
    Fetches rhyming words using the Datamuse API, cached for 1 hour.
    """
    try:
        response = requests.get(f"https://api.datamuse.com/words?rel_rhy={word}&max=10")
        if response.status_code == 200:
            return [item["word"] for item in response.json()]
    except Exception:
        pass
    return []

def count_syllables(word):
    """
    Counts syllables in a word using the Pronouncing library (fallback to vowels if not found).
    """
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    # Fallback: simple vowel-based estimation
    return sum(1 for char in word.lower() if char in "aeiou")

def rhythm_feedback(syllable_counts):
    """
    Provides feedback on the rhythm based on syllable consistency.
    """
    if not syllable_counts:
        return "No rhythm detected."
    diffs = [abs(syllable_counts[i] - syllable_counts[i - 1]) for i in range(1, len(syllable_counts))]
    avg_diff = sum(diffs) / len(diffs) if diffs else 0
    if avg_diff <= 1:
        return "🎵 Smooth rhythm (consistent syllable pattern)"
    elif avg_diff <= 2:
        return "🎶 Slightly uneven rhythm"
    else:
        return "⚡ Irregular rhythm (consider adjusting syllables)"

# =========================
# STREAMLIT APP
# =========================
def main():
    st.set_page_config(page_title="Melosphere AI", page_icon="🎶", layout="centered")
    st.title("🎶 Melosphere AI — Lyrics Without Limits")

    st.divider()
    st.markdown("### 📝 Enter Your Lyrics")
    lyric_line = st.text_area("Type your lyric line(s) below:", height=120, placeholder="e.g. The stars above remind me of your eyes")

    st.markdown("### 🌍 Select Target Language")
    languages = {
        "Spanish": "es",
        "Kannada": "kn",
        "Tamil": "ta",
        "Malayalam": "ml",
        "Hindi": "hi",
        "Telugu": "te",
        "Japanese": "ja",
    }

    tgt_lang = st.selectbox("Target language:", list(languages.keys()))

    st.divider()

    if st.button("🎧 Generate Analysis & Translation"):
        if lyric_line.strip():
            words = lyric_line.strip().split()
            last_word = words[-1].lower()

            # --- Rhyme Section ---
            with st.expander("🎤 Rhyme Suggestions"):
                rhymes = get_rhymes_cached(last_word)
                if rhymes:
                    st.success(f"Rhymes for **'{last_word}'**: {', '.join(rhymes)}")
                else:
                    st.warning(f"No rhymes found for '{last_word}'.")

            # --- Rhythm Section ---
            with st.expander("🎼 Rhythm & Syllable Analysis"):
                syllable_counts = [count_syllables(w) for w in words]
                rhythm = rhythm_feedback(syllable_counts)
                st.write(f"**Syllables per word:** {dict(zip(words, syllable_counts))}")
                st.write(f"**Total syllables:** {sum(syllable_counts)}")
                st.info(rhythm)

            # --- Translation Section ---
            with st.expander("🌐 Multilingual Translation"):
                tgt_code = languages[tgt_lang]
                translation = translate_cached(lyric_line, tgt_code)
                st.markdown(f"**{tgt_lang} Translation:**")
                st.success(translation)

            st.balloons()
        else:
            st.warning("⚠️ Please enter lyrics first.")

    # Footer
    st.divider()
    st.caption("🚀 Melosphere AI — Phase 1 Prototype | Powered by Deep Translator, Datamuse & Pronouncing")

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    main()
