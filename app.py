import streamlit as st
import random
import re
import plotly.graph_objects as go
from gtts import gTTS
from io import BytesIO
from googletrans import Translator
import pyphen

# ==========================
# 🎨 PAGE CONFIG & STYLE
# ==========================
st.set_page_config(
    page_title="🎛️ Melosphere — Polyglot Lyric Blending",
    page_icon="🎧",
    layout="wide"
)

st.markdown("""
    <style>
        /* Page background gradient */
        body {
            background: linear-gradient(135deg, #f0f4ff, #e8faff, #f9fcff);
            background-attachment: fixed;
            font-family: 'Poppins', sans-serif;
        }

        /* Title */
        .main-title {
            font-size: 2.8rem;
            font-weight: 800;
            text-align: center;
            background: linear-gradient(90deg, #007CF0, #00DFD8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-top: 10px;
            margin-bottom: 5px;
        }
        .subtitle {
            text-align: center;
            font-size: 1.1rem;
            color: #444;
            margin-bottom: 25px;
        }

        /* Text area styling */
        textarea {
            background-color: #000 !important;
            color: #fff !important;
            border: 2px solid #444 !important;
            border-radius: 10px !important;
            transition: all 0.3s ease-in-out;
        }
        textarea:focus {
            border-color: #00DFD8 !important;
            box-shadow: 0 0 12px rgba(0, 223, 216, 0.6);
        }

        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            justify-content: center;
            gap: 1.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
            background: #f1f6ff;
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
            transition: all 0.3s ease-in-out;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: linear-gradient(90deg, #e0f7ff, #dff5ff);
            color: #007CF0;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(90deg, #007CF0, #00DFD8);
            color: white !important;
            box-shadow: 0 0 10px rgba(0, 223, 216, 0.6);
        }

        /* Audio container */
        .audio-box {
            background: linear-gradient(90deg, #222, #444);
            color: white;
            border-radius: 15px;
            padding: 15px;
            text-align: center;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>🎛️ Melosphere — Polyglot Lyric Blending</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Rhythmic translation & polyglot blending — enhanced ✨</div>", unsafe_allow_html=True)

# ==========================
# UTILITIES
# ==========================
translator = Translator()
dic_en = pyphen.Pyphen(lang='en')

def clean_text(text):
    text = re.sub(r"[^a-zA-Z0-9\s,.!?']", '', text)
    return text.strip()

def count_syllables(word):
    return len(dic_en.inserted(word).split('-'))

def get_pronunciation_guide(lang, text):
    if lang == 'ja':
        return re.sub(r'([ぁ-んァ-ン一-龥])', r'\1·', text)
    else:
        return ' '.join(re.sub(r'([A-Za-z])', r'\1·', text))

def generate_audio(text, lang):
    mp3_fp = BytesIO()
    tts = gTTS(text=text, lang=lang)
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    return mp3_fp

def blend_words(words1, words2):
    blended = []
    for w1, w2 in zip(words1, words2):
        choice = random.choice([w1, w2])
        blended.append(choice)
    return ' '.join(blended)

def plot_syllables_chart(lyrics, syllable_counts):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(range(1, len(syllable_counts)+1)),
        y=syllable_counts,
        text=lyrics.split(),
        textposition='auto',
        marker=dict(color='rgba(0, 223, 216, 0.7)')
    ))
    fig.update_layout(
        title="Syllable Rhythm Pattern",
        xaxis_title="Word Position",
        yaxis_title="Syllable Count",
        template="plotly_white"
    )
    return fig

# ==========================
# MAIN APP
# ==========================
lyrics_input = st.text_area(
    "Enter your lyrics ✍️",
    placeholder="e.g. You're my sunshine, my only sunshine...",
    height=150
)

target_langs = st.multiselect(
    "Select target languages for translation 🌐",
    ["ja", "fr", "es", "hi", "de"],
    default=["ja", "fr"]
)

if st.button("🌈 Blend My Lyrics"):
    if lyrics_input:
        cleaned = clean_text(lyrics_input)
        words = cleaned.split()
        syllable_counts = [count_syllables(w) for w in words]

        # Translations
        translations = {}
        for lang in target_langs:
            translations[lang] = translator.translate(cleaned, dest=lang).text

        # Blended text
        blended_texts = {}
        for lang in target_langs:
            trans_words = translations[lang].split()
            blended_texts[lang] = blend_words(words, trans_words)

        # Tabs for sections
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🌐 Translation", "🎭 Blended Output", "📊 Charts", "📖 Pronunciation Guide", "🔊 Audio"
        ])

        with tab1:
            st.subheader("🌍 Translated Lyrics")
            for lang, text in translations.items():
                st.markdown(f"**{lang.upper()}**: {text}")

        with tab2:
            st.subheader("🎶 Blended Polyglot Lyrics")
            for lang, text in blended_texts.items():
                st.markdown(f"**{lang.upper()} Blend:** {text}")

        with tab3:
            st.subheader("📊 Rhythm Syllable Visualization")
            fig = plot_syllables_chart(cleaned, syllable_counts)
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.subheader("📖 Pronunciation Guides")
            for lang, text in translations.items():
                guide = get_pronunciation_guide(lang, text)
                st.markdown(f"**{lang.upper()} Guide:** {guide}")

        with tab5:
            st.subheader("🎧 Listen to Translations")
            for lang, text in translations.items():
                with st.container():
                    st.markdown(f"<div class='audio-box'><b>{lang.upper()}</b></div>", unsafe_allow_html=True)
                    audio_fp = generate_audio(text, lang)
                    st.audio(audio_fp, format='audio/mp3')
    else:
        st.warning("Please enter some lyrics to start blending! 🎵")
