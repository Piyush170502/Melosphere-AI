import streamlit as st
import requests
import pronouncing
import math
import plotly.graph_objects as go
from gtts import gTTS
import tempfile
import base64
from google.cloud import translate_v2 as translate
import os
import re

# ------------------------
# Initialize Translate Client Once
# ------------------------
@st.cache_resource
def get_translate_client():
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = st.secrets["general"]["GOOGLE_APPLICATION_CREDENTIALS"]
    except Exception:
        pass
    return translate.Client()

translator_client = get_translate_client()

# ------------------------
# Translation Helper
# ------------------------
def translate_text(text, target_lang):
    try:
        result = translator_client.translate(text, target_language=target_lang)
        return result["translatedText"]
    except Exception as e:
        return f"⚠️ Translation failed: {e}"

# ------------------------
# Rhymes & Syllables
# ------------------------
def count_syllables_english(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for ch in word.lower() if ch in 'aeiou')

def count_syllables_heuristic(text):
    if not text:
        return 0
    text = re.sub(r"[^a-zA-Záàâäãåāéèêëēíìîïīóòôöõōúùûüūy\s]", " ", text)
    words = text.split()
    vowels = "aeiouáàâäãåāéèêëēíìîïīóòôöõōúùûüūy"
    total = 0
    for w in words:
        w = w.lower()
        count = 0
        prev = False
        for ch in w:
            is_v = ch in vowels
            if is_v and not prev:
                count += 1
            prev = is_v
        total += count or 1
    return total

def count_syllables_general(text, lang_code):
    if lang_code.startswith("en"):
        return sum(count_syllables_english(w) for w in text.split())
    return count_syllables_heuristic(text)

# ------------------------
# Rhythm Enhancement
# ------------------------
FILLERS = ["oh", "yeah", "ah", "la", "na", "hey", "woo", "mmm"]

def enhance_rhythm(translation, target_syllables):
    words = translation.split()
    current = count_syllables_heuristic(translation)
    diff = target_syllables - current
    if diff <= 0:
        return translation
    new_words = []
    gap = max(1, len(words) // diff)
    f = 0
    for i, w in enumerate(words):
        new_words.append(w)
        if i % gap == 0 and diff > 0:
            new_words.append(FILLERS[f % len(FILLERS)])
            f += 1
            diff -= 1
    return " ".join(new_words)

# ------------------------
# Stress/Beat Alignment
# ------------------------
def stress_align(translation, target_syllables):
    words = translation.split()
    beat_ratio = max(1, target_syllables // (len(words) + 1))
    adjusted = []
    for i, w in enumerate(words):
        adjusted.append(w)
        if (i + 1) % beat_ratio == 0:
            adjusted.append("⋅")
    return " ".join(adjusted)

# ------------------------
# Phonetics + Audio
# ------------------------
def simple_phonetic(text):
    t = text.lower()
    t = t.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    t = t.replace("ñ", "ny").replace("ç", "s")
    return re.sub(r"[^a-z\s]", "", t)

def ipa_transcription(text):
    ipa = text.lower()
    ipa = ipa.replace("a", "ɑ").replace("e", "ɛ").replace("i", "iː").replace("o", "ɔ").replace("u", "uː")
    ipa = ipa.replace("th", "θ").replace("sh", "ʃ").replace("ch", "tʃ").replace("ph", "f")
    return re.sub(r"[^ɑɛiːɔuːθʃtʃf\s]", "", ipa)

def generate_tts_audio(text, lang_code):
    try:
        tts = gTTS(text=text, lang=lang_code)
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_path.name)
        with open(temp_path.name, "rb") as f:
            audio_bytes = f.read()
        b64 = base64.b64encode(audio_bytes).decode()
        return f'<audio controls src="data:audio/mp3;base64,{b64}"></audio>'
    except Exception as e:
        return f"⚠️ Audio generation failed: {e}"

# ------------------------
# Visualization
# ------------------------
def syllable_dots(count):
    return "• " * int(count)

def plot_syllable_chart(data_dict, source_syllables):
    langs = list(data_dict.keys())
    vals = list(data_dict.values())
    colors = ['#1f77b4' if abs(v - source_syllables) <= 2 else '#ff7f0e' for v in vals]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=langs, y=vals, marker_color=colors))
    fig.add_hline(y=source_syllables, line_dash="dot", annotation_text="Source Syllables", annotation_position="top right")
    fig.update_layout(height=300, title="Syllable Comparison", xaxis_title="Language", yaxis_title="Syllables")
    return fig

# ------------------------
# Streamlit UI
# ------------------------
def main():
    st.set_page_config(page_title="Melosphere — Polyglot + Rhythm + Phonetics", layout="wide")
    st.title("🎶 Melosphere — Polyglot Blending + Rhythm + Pronunciation")

    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("Enter lyric line (English):", height=80)
    with col2:
        langs = {
            "Spanish": "es", "Kannada": "kn", "Tamil": "ta", "Malayalam": "ml",
            "Hindi": "hi", "Telugu": "te", "Japanese": "ja", "French": "fr",
            "Portuguese": "pt", "German": "de", "Korean": "ko"
        }
        selected = st.multiselect("Select 2+ target languages:", list(langs.keys()), default=["Spanish", "Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])
        show_chart = st.checkbox("Show syllable chart", value=False)
        show_rhythm = st.checkbox("Apply rhythmic enhancement", value=False)
        show_stress = st.checkbox("Show stress/beat alignment", value=False)
        phonetic_toggle = st.toggle("Use simplified phonetic style (default = IPA)", value=False)

    if not lyric_line or not selected:
        st.info("Enter a lyric line and select languages.")
        return

    src_syll = count_syllables_general(lyric_line, "en")

    translations = {}
    for name in selected:
        code = langs[name]
        trans = translate_text(lyric_line, code)
        if show_rhythm:
            trans = enhance_rhythm(trans, src_syll)
        if show_stress:
            trans = stress_align(trans, src_syll)
        translations[name] = trans

    st.subheader("Translations")
    cols = st.columns(len(selected))
    for col, name in zip(cols, selected):
        with col:
            st.markdown(f"**{name}**")
            st.write(translations[name])

    # Syllables
    st.subheader("Syllable Analysis")
    st.write(f"**English (source):** {src_syll} syllables")
    counts = {l: count_syllables_general(t, langs[l]) for l, t in translations.items()}
    for l, c in counts.items():
        diff = c - src_syll
        st.write(f"{l}: {c} ({'+' if diff>0 else ''}{diff}) {syllable_dots(c)}")

    if show_chart:
        st.plotly_chart(plot_syllable_chart(counts, src_syll), use_container_width=True)

    # Pronunciation
    st.subheader("Pronunciation Guide")
    for l, t in translations.items():
        lang_code = langs[l]
        ipa = ipa_transcription(t)
        simp = simple_phonetic(t)
        st.markdown(f"**{l}:**")
        st.markdown(simp if phonetic_toggle else ipa)
        st.markdown(generate_tts_audio(t, lang_code), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
