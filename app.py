import streamlit as st
import requests
import pronouncing
import os
import tempfile
import plotly.graph_objects as go
from googletrans import Translator
from gtts import gTTS
import eng_to_ipa as ipa
from pydub import AudioSegment
from pydub.playback import play

# ======================================
# Utility: Translate text (GoogleTrans)
# ======================================

def translate_text(text, target_lang):
    translator = Translator()
    try:
        translation = translator.translate(text, dest=target_lang)
        return translation.text
    except Exception as e:
        return f"Error during translation: {e}"

# ======================================
# Utility: Syllable & Rhymes
# ======================================

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
        return sum(1 for ch in word.lower() if ch in 'aeiou')

def syllable_dots(count):
    return "•" * count

# ======================================
# Pronunciation Guide System
# ======================================

def get_pronunciations(text, simplified=False):
    words = text.split()
    ipa_text = []
    simple_text = []
    for w in words:
        ipa_form = ipa.convert(w)
        ipa_text.append(ipa_form if ipa_form else w)
        simple_form = w.replace("th", "t").replace("ph", "f").replace("gh", "g")
        simple_text.append(simple_form)
    if simplified:
        return " ".join(simple_text)
    else:
        return " ".join(ipa_text)

def generate_audio(text, lang="en"):
    try:
        tts = gTTS(text=text, lang=lang)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return tmp.name
    except Exception as e:
        return None

# ======================================
# Rhythmic Enhancements
# ======================================

def rhythmic_adjustment(source_line, target_line):
    src_syllables = sum(count_syllables(w) for w in source_line.split())
    tgt_syllables = sum(count_syllables(w) for w in target_line.split())

    fillers = ["oh", "yeah", "ah", "na", "la"]
    adjusted_line = target_line

    diff = src_syllables - tgt_syllables
    if diff > 0:
        insert_positions = list(range(1, len(target_line.split()), max(1, len(target_line.split()) // diff)))[:diff]
        words = target_line.split()
        for i, pos in enumerate(insert_positions):
            if pos < len(words):
                words.insert(pos, fillers[i % len(fillers)])
        adjusted_line = " ".join(words)

    return adjusted_line

# ======================================
# Syllable Visualizer
# ======================================

def plot_syllable_comparison(src, tgt):
    src_s = sum(count_syllables(w) for w in src.split())
    tgt_s = sum(count_syllables(w) for w in tgt.split())

    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Source"], y=[src_s], name="Source", marker_color="#1f77b4"))
    fig.add_trace(go.Bar(x=["Target"], y=[tgt_s], name="Target", marker_color="#ff7f0e"))
    fig.update_layout(
        title="Syllable Count Comparison",
        xaxis_title="Line Type",
        yaxis_title="Syllables",
        barmode="group",
        height=300,
    )
    return fig

# ======================================
# Streamlit App
# ======================================

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
    show_chart = st.toggle("Show Syllable Chart")
    show_pronunciation = st.toggle("Show Pronunciation Guide")
    simplified_toggle = st.toggle("Show Simplified Phonetic Style")

    if lyric_line:
        # --- Rhymes ---
        words = lyric_line.strip().split()
        last_word = words[-1].lower()
        rhymes = get_rhymes(last_word)
        if rhymes:
            st.write(f"**Rhymes for '{last_word}':** {', '.join(rhymes)}")
        else:
            st.write(f"No rhymes found for '{last_word}'.")

        # --- Translation ---
        translation = translate_text(lyric_line, languages[tgt_lang])

        # --- Rhythmic Enhancement ---
        rhythmic_version = rhythmic_adjustment(lyric_line, translation)

        # --- Pronunciation Guides ---
        if show_pronunciation:
            st.subheader("🎙️ Pronunciation Guide")
            ipa_version = get_pronunciations(translation, simplified=False)
            simplified_version = get_pronunciations(translation, simplified=True)
            if simplified_toggle:
                st.text_area("Simplified Phonetic Style:", simplified_version, height=100)
            else:
                st.text_area("IPA Style Transcription:", ipa_version, height=100)

            audio_file = generate_audio(translation, lang=languages[tgt_lang])
            if audio_file:
                st.audio(audio_file, format="audio/mp3")

        # --- Output Sections ---
        st.write(f"**{tgt_lang} Translation:** {translation}")
        st.write(f"**Rhythmically Enhanced Translation:** {rhythmic_version}")

        # --- Syllable Visualizer ---
        if show_chart:
            st.plotly_chart(plot_syllable_comparison(lyric_line, rhythmic_version))

        # --- Syllable Breakdown ---
        src_syllables = sum(count_syllables(w) for w in lyric_line.split())
        tgt_syllables = sum(count_syllables(w) for w in rhythmic_version.split())
        st.write(f"🎵 **Source Syllables:** {src_syllables}  |  **Target (Enhanced):** {tgt_syllables}")

        dots_src = syllable_dots(src_syllables)
        dots_tgt = syllable_dots(tgt_syllables)
        st.write(f"🔵 Source Pattern: {dots_src}")
        st.write(f"🟠 Target Pattern: {dots_tgt}")

    st.caption("Stress/beat alignment support is prepared as a placeholder — will expand to real prosody modeling next.")

if __name__ == "__main__":
    main()
