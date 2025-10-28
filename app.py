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
# Setup Google Translate client
# ------------------------
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
def get_rhymes(word):
    try:
        response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10', timeout=6)
        if response.status_code == 200:
            return [item['word'] for item in response.json()]
    except Exception:
        pass
    return []

def count_syllables_english(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for ch in word.lower() if ch in 'aeiou')

def count_syllables_heuristic(text):
    if not text:
        return 0
    text = re.sub(r"[^a-zA-Záàâäãåāéèêëēíìîïīóòôöõōúùûüūy\s]", " ", str(text))
    words = text.split()
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
    if lang_code.startswith("en"):
        words = [w for w in text.split() if w.strip()]
        return sum(count_syllables_english(w) for w in words)
    return count_syllables_heuristic(text)

# ------------------------
# Rhythmic Enhancement (natural fillers)
# ------------------------
FILLERS = ["oh", "yeah", "ah", "la", "na", "hey", "woo", "mmm"]

def enhance_rhythm(translation, target_syllables):
    words = translation.split()
    current_syllables = count_syllables_heuristic(translation)
    diff = target_syllables - current_syllables
    if diff <= 0:
        return translation

    insert_positions = []
    if len(words) > 2:
        insert_positions = list(range(1, len(words), max(1, len(words)//diff)))
    else:
        insert_positions = [len(words)//2] * diff

    new_words = []
    filler_index = 0
    for i, word in enumerate(words):
        new_words.append(word)
        if i in insert_positions and diff > 0:
            new_words.append(FILLERS[filler_index % len(FILLERS)])
            filler_index += 1
            diff -= 1
    return " ".join(new_words)

# ------------------------
# Stress/Beat Alignment (placeholder logic)
# ------------------------
def stress_align(translation, target_syllables):
    # Placeholder for real beat-matching logic
    # Slight rhythm adjustment markers (⋅) for visually balanced alignment
    words = translation.split()
    adjusted = []
    beat_ratio = max(1, target_syllables // (len(words) + 1))
    for i, w in enumerate(words):
        adjusted.append(w)
        if (i + 1) % beat_ratio == 0:
            adjusted.append("⋅")
    return " ".join(adjusted)

# ------------------------
# Phonetic Transcription Helpers
# ------------------------
def simple_phonetic(text):
    translit = text.lower()
    translit = translit.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    translit = translit.replace("ñ", "ny").replace("ç", "s")
    translit = re.sub(r"[^a-z\s]", "", translit)
    return translit

def ipa_transcription(text):
    # Very approximate placeholder IPA
    ipa = text.lower()
    ipa = ipa.replace("a", "ɑ").replace("e", "ɛ").replace("i", "iː").replace("o", "ɔ").replace("u", "uː")
    ipa = ipa.replace("th", "θ").replace("sh", "ʃ").replace("ch", "tʃ").replace("ph", "f")
    ipa = re.sub(r"[^ɑɛiːɔuːθʃtʃf\s]", "", ipa)
    return ipa

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
# Visualization Helpers
# ------------------------
def syllable_dots(count):
    return "• " * int(count)

def plot_syllable_chart(data_dict, source_syllables):
    langs = list(data_dict.keys())
    values = list(data_dict.values())
    colors = ['#1f77b4' if abs(v - source_syllables) <= 2 else '#ff7f0e' for v in values]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=langs, y=values, marker_color=colors))
    fig.add_hline(y=source_syllables, line_dash="dot", annotation_text="Source Syllables", annotation_position="top right")
    fig.update_layout(height=300, title="Syllable Comparison Across Languages", xaxis_title="Language", yaxis_title="Syllables")
    return fig

# ------------------------
# Streamlit UI
# ------------------------
def main():
    st.set_page_config(page_title="Melosphere — Polyglot + Rhythm + Phonetics", layout="wide")
    st.title("🎶 Melosphere — Polyglot Blending + Rhythmic & Pronunciation System")

    st.markdown("""
    Combine multilingual lyric translations with rhythmic alignment and pronunciation guidance.
    """)

    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("Enter your lyric line (English):", height=80)
    with col2:
        available_languages = {
            "Spanish": "es", "Kannada": "kn", "Tamil": "ta", "Malayalam": "ml",
            "Hindi": "hi", "Telugu": "te", "Japanese": "ja", "French": "fr",
            "Portuguese": "pt", "German": "de", "Korean": "ko"
        }
        selected = st.multiselect("Select 2+ target languages:", list(available_languages.keys()), default=["Spanish", "Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])
        show_chart = st.checkbox("Show syllable comparison chart", value=False)
        show_rhythm = st.checkbox("Apply rhythmic enhancement", value=False)
        show_stress = st.checkbox("Show stress/beat alignment", value=False)
        phonetic_toggle = st.toggle("Show simplified phonetic style (default = IPA)", value=False)

    if not lyric_line or not selected:
        st.info("Enter a lyric line and select languages.")
        return

    # Translations
    tgt_codes = [available_languages[l] for l in selected]
    translations = {}
    for lang_name, code in zip(selected, tgt_codes):
        trans = translate_text(lyric_line, code)
        if show_rhythm:
            trans = enhance_rhythm(trans, count_syllables_general(lyric_line, "en"))
        if show_stress:
            trans = stress_align(trans, count_syllables_general(lyric_line, "en"))
        translations[lang_name] = trans

    st.subheader("Translations")
    cols = st.columns(len(selected))
    for col, lang_name in zip(cols, selected):
        with col:
            st.markdown(f"**{lang_name}**")
            st.write(translations[lang_name])

    # Syllables
    st.subheader("Syllable Analysis")
    src_syll = count_syllables_general(lyric_line, "en")
    syll_counts = {l: count_syllables_general(t, available_languages[l]) for l, t in translations.items()}
    st.write(f"**Source (English):** {src_syll} syllables")
    for l, s in syll_counts.items():
        diff = s - src_syll
        st.write(f"{l}: {s} ({'+' if diff>0 else ''}{diff})  {syllable_dots(s)}")

    if show_chart:
        fig = plot_syllable_chart(syll_counts, src_syll)
        st.plotly_chart(fig, use_container_width=True)

    # Pronunciation
    st.subheader("Pronunciation Guide")
    for l, t in translations.items():
        lang_code = available_languages[l]
        ipa = ipa_transcription(t)
        simp = simple_phonetic(t)
        st.markdown(f"**{l} Pronunciation:**")
        st.markdown(ipa if not phonetic_toggle else simp)
        audio_html = generate_tts_audio(t, lang_code)
        st.markdown(audio_html, unsafe_allow_html=True)

    st.success("✅ Stress/beat alignment placeholder active — real prosody matching will follow next phase.")

if __name__ == "__main__":
    main()
