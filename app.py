import streamlit as st
import requests
import pronouncing
import math
import random
import re
import plotly.graph_objects as go
from gtts import gTTS
import tempfile
import base64
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
import epitran
from indic_transliteration.sanscript import transliterate
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import io

# ------------------------
# Page Config & Animated Gradient
# ------------------------
st.set_page_config(page_title="Melosphere — Polyglot Blending", layout="wide")

st.markdown(
    """
    <style>
    html, body, [class*="css"]  {
        background: linear-gradient(120deg, #f4f7ff 0%, #fffaf6 50%, #f9fbff 100%);
        background-size: 300% 300%;
        animation: gradientShift 18s ease infinite;
        font-family: 'Poppins', system-ui, sans-serif;
    }
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .main-header {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 800;
        margin-top: 10px;
        margin-bottom: 4px;
        background: linear-gradient(90deg, #7c5cff, #ff7ab6, #ffb86b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        text-align: center;
        color: #6b7280;
        margin-top: -6px;
        margin-bottom: 24px;
        font-size: 1rem;
    }

    textarea {
        background-color: #000 !important;
        color: #fff !important;
        border-radius: 10px !important;
        border: 2px solid #555 !important;
        padding: 12px !important;
        font-size: 16px !important;
        line-height: 1.5 !important;
        transition: 0.3s all ease-in-out;
    }
    textarea:focus {
        border-color: #ff7ab6 !important;
        box-shadow: 0 0 15px rgba(255,122,182,0.5);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
        gap: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 1.1rem;
        border-radius: 10px;
        background: rgba(255,255,255,0.6);
        color: #333;
        transition: all 0.3s ease-in-out;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: linear-gradient(90deg, #fcecff, #eaf6ff);
        color: #7c5cff;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #7c5cff, #ff7ab6);
        color: white !important;
        box-shadow: 0 0 10px rgba(124,92,255,0.4);
    }

    .audio-box {
        background: linear-gradient(90deg, #2a2a2a, #3d3d3d);
        padding: 15px;
        border-radius: 15px;
        color: white;
        margin-top: 10px;
        margin-bottom: 15px;
        text-align: center;
    }

    div.stButton > button {
        background: linear-gradient(90deg, #7c5cff, #ff7ab6);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-header">🎛️ Melosphere — Polyglot Lyric Blending</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Rhythmic translation & polyglot blending — enhanced ✨</div>', unsafe_allow_html=True)

# ------------------------
# Logging
# ------------------------
if "melosphere_logs" not in st.session_state:
    st.session_state["melosphere_logs"] = ""

def log(msg: str):
    st.session_state["melosphere_logs"] += msg + "\n"

# ------------------------
# Google Translate
# ------------------------
@st.cache_resource
def get_translate_client():
    try:
        credentials_info = st.secrets["gcp_service_account"]
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = translate.Client(credentials=credentials)
        log("✅ Translate client initialized")
        return client
    except Exception as e:
        log(f"❌ Translate init error: {e}")
        return None

translate_client = get_translate_client()

def translate_text(text, target_lang):
    if not translate_client:
        return "⚠️ Translation client not initialized."
    try:
        result = translate_client.translate(text, target_language=target_lang)
        return result.get("translatedText", "")
    except Exception as e:
        log(f"⚠️ Translation error: {e}")
        return str(e)

# ------------------------
# Helpers
# ------------------------
def clean_text(text):
    return str(text).strip().replace("“", '"').replace("”", '"')

def count_syllables_heuristic(text):
    text = str(text)
    for ch in ",.!?;:-—()\"'":
        text = text.replace(ch, " ")
    words = [w for w in text.split() if w.strip()]
    vowels = "aeiouáàâäãåāéèêëēíìîïīóòôöõōúùûüūy"
    syllables = 0
    for w in words:
        lw = w.lower()
        groups = 0
        prev_vowel = False
        for ch in lw:
            is_v = ch in vowels
            if is_v and not prev_vowel:
                groups += 1
            prev_vowel = is_v
        if groups == 0:
            groups = 1
        syllables += groups
    return syllables

_FILLERS = ["oh", "la", "yeah", "na", "hey", "mmm"]

def _build_fillers(diff, max_fillers=3, seed_text=None):
    k = min(max_fillers, max(0, diff))
    if k == 0: return ""
    rnd = random.Random(int(hashlib.sha256(seed_text.encode()).hexdigest()[:8], 16))
    return " ".join(rnd.choices(_FILLERS, k=k))

def insert_fillers_safely(text, fillers):
    t = text.strip()
    return f"{t}, {fillers}" if fillers else t

def rhythmic_translation_enhancement(original, translated):
    orig_syll = count_syllables_heuristic(original)
    trans_syll = count_syllables_heuristic(translated)
    diff = orig_syll - trans_syll
    if diff > 0:
        fillers = _build_fillers(diff, seed_text=original + translated)
        enhanced = insert_fillers_safely(translated, fillers)
    else:
        enhanced = translated
    return enhanced

def interleave_words(original, translations):
    tokenized = [t.split() for t in translations]
    max_len = max(len(t) for t in tokenized)
    out = []
    for i in range(max_len):
        for t in tokenized:
            if i < len(t): out.append(t[i])
    return " ".join(out)

def phrase_swap(original, translations):
    halves = [t.split()[:len(t.split())//2] for t in translations]
    return " ".join(sum(halves, []))

def last_word_swap(original, translations):
    orig_words = original.split()
    for t in translations:
        tw = t.split()
        if tw: orig_words[-1] = tw[-1]
    return " ".join(orig_words)

def generate_tts_audio(text, lang):
    try:
        tts = gTTS(text=text, lang=lang)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        with open(tmp.name, "rb") as f: b64 = base64.b64encode(f.read()).decode()
        return f'<audio controls src="data:audio/mp3;base64,{b64}"></audio>'
    except Exception as e:
        return f"<i>Audio unavailable: {e}</i>"

def get_pronunciation(text, lang):
    ipa = text.replace("th","θ").replace("sh","ʃ").replace("ch","tʃ").replace("ph","f")
    return ipa

# ------------------------
# MAIN APP
# ------------------------
def main():
    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("Enter your lyric line (English):", height=100, placeholder="You're my sunshine 🌞")
    with col2:
        langs = {
            "Spanish": "es", "Hindi": "hi", "Japanese": "ja", "French": "fr",
            "German": "de", "Tamil": "ta", "Kannada": "kn"
        }
        selected = st.multiselect("Select languages:", list(langs.keys()), default=["Spanish","Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])

    if not lyric_line or not selected:
        st.info("Enter a lyric and select at least one target language.")
        return

    lyric_line_clean = clean_text(lyric_line)
    translations, enhanced = {}, {}

    # parallel translation
    def process(lang_name, code):
        trans = translate_text(lyric_line_clean, code)
        enh = rhythmic_translation_enhancement(lyric_line_clean, trans)
        return lang_name, code, trans, enh

    with ThreadPoolExecutor() as ex:
        futures = [ex.submit(process, l, langs[l]) for l in selected]
        for f in as_completed(futures):
            ln, code, trans, enh = f.result()
            translations[ln] = trans
            enhanced[ln] = enh

    translations_list = [enhanced[l] for l in selected]
    if mode == "Interleave Words":
        blended = interleave_words(lyric_line_clean, translations_list)
    elif mode == "Phrase Swap":
        blended = phrase_swap(lyric_line_clean, translations_list)
    else:
        blended = last_word_swap(lyric_line_clean, translations_list)

    # ---- TABS ----
    tab1, tab2, tab3, tab4 = st.tabs(["🌐 Translations", "🎭 Blended Output", "📊 Charts", "🎙️ Pronunciation + Audio"])

    with tab1:
        for l in selected:
            st.markdown(f"**{l}** — {translations[l]}")

    with tab2:
        st.info(f"**Blended Output:** {blended}")

    with tab3:
        fig = go.Figure(go.Bar(x=["Original","Avg Translation"], y=[count_syllables_heuristic(lyric_line_clean),
               sum(count_syllables_heuristic(t) for t in translations.values())/len(translations)],
               marker_color=["#7c5cff","#ff7ab6"]))
        fig.update_layout(title="Syllable Comparison", yaxis_title="Count", height=300)
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        for l in selected:
            code = langs[l]
            st.markdown(f"**{l} Pronunciation:**")
            st.markdown(get_pronunciation(translations[l], code))
            st.markdown(f"<div class='audio-box'>{generate_tts_audio(translations[l], code)}</div>", unsafe_allow_html=True)

    with st.sidebar:
        st.subheader("Logs")
        st.text_area("Runtime logs:", value=st.session_state["melosphere_logs"], height=300)

if __name__ == "__main__":
    main()
