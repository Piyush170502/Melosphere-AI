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
# Page & Animated CSS UI
# ------------------------
st.set_page_config(page_title="Melosphere — Polyglot Blending", layout="wide")

st.markdown(
    """
    <style>
    /* Animated pale gradient background */
    html, body, [class*="css"] {
        background: linear-gradient(120deg, #fbfbff 0%, #f4f7ff 25%, #fffaf6 50%, #f9fbff 75%, #ffffff 100%);
        background-size: 300% 300%;
        animation: gradientShift 18s ease infinite;
        font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Header gradient text */
    .main-header {
        text-align: center;
        font-size: 30px;
        font-weight: 800;
        margin-bottom: 4px;
        background: linear-gradient(90deg, #7c5cff, #ff7ab6, #ffb86b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-block;
        padding: 6px 12px;
        border-radius: 12px;
    }
    .sub-header {
        text-align: center;
        color: #6b7280;
        margin-top: -6px;
        margin-bottom: 18px;
        font-size: 14px;
    }

    /* Modern dark textarea style (input) */
    textarea {
        border-radius: 12px !important;
        border: 1px solid #3a3a3a !important;
        padding: 12px !important;
        transition: box-shadow 0.18s ease, border-color 0.18s ease, background 0.3s ease;
        font-size: 16px !important;
        line-height: 1.5 !important;
        background: #000 !important; /* Black background */
        color: #f1f1f1 !important; /* Light text for contrast */
        resize: vertical !important;
        caret-color: #9b6bff !important; /* Stylish purple cursor */
    }

    /* Focus effect */
    textarea:focus {
        border-color: rgba(124, 92, 255, 0.9) !important;
        box-shadow: 0 0 12px rgba(124, 92, 255, 0.35) !important;
        outline: none !important;
        background: #0a0a0a !important; /* Slightly lighter on focus */
    }

    /* Typing animation */
    @keyframes textPulse {
        0% { text-shadow: 0 0 0 rgba(124, 92, 255, 0); }
        50% { text-shadow: 0 0 6px rgba(124, 92, 255, 0.4); }
        100% { text-shadow: 0 0 0 rgba(124, 92, 255, 0); }
    }

    /* Animate text glow while typing */
    textarea:focus:not(:placeholder-shown) {
        animation: textPulse 1.4s ease-in-out infinite;
    }

    /* --- TAB STYLES (MODIFIED) --- */
    div[data-testid="stTab"] button {
        /* 1. Black background for the tab buttons */
        background-color: black !important;
        color: #a0a0a0; /* Default color for inactive text */
        border-radius: 8px 8px 0 0 !important;
        border: none !important;
        padding: 10px 15px !important;
        transition: all 0.2s ease;
        font-weight: 500;
    }

    /* Target the container of the tab labels to set background to black */
    div[data-testid="stTabs"] {
        background-color: black;
        padding: 0 10px 0 10px; /* Optional: adds a bit of padding around the tabs */
        border-radius: 10px 10px 0 0;
    }
    
    /* Active Tab: Gradient Text and Gradient Border */
    div[data-testid="stTab"] button[aria-selected="true"] {
        /* 2. Gradient text for the active tab */
        background: linear-gradient(90deg, #7c5cff, #ff7ab6) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        
        /* Ensure background stays black and is on top */
        background-color: black !important; 
        font-weight: 700;

        /* 3. Gradient Border (using border-image for a bottom underline effect) */
        border-bottom: 4px solid;
        border-image: linear-gradient(to right, #7c5cff, #ff7ab6) 1;
        border-image-slice: 1;
        border-radius: 0 !important; 
    }

    /* Inactive Tab Border: Dark Solid Line */
    div[data-testid="stTab"] button:not([aria-selected="true"]) {
        border-bottom: 4px solid #444 !important;
    }
    /* The space under the tabs needs a dark background to blend */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: black; 
    }
    /* Set the content area after the tabs back to white/transparent to match the body */
    .st-emotion-cache-1cpxdwv { /* This targets the content area below the tab bar */
        background: transparent !important;
    }
    /* ------------------------------------ */


    /* Gradient text for output headers */
    .output-header {
        font-size: 20px;
        font-weight: 700;
        margin-top: 15px;
        margin-bottom: 5px;
        background: linear-gradient(90deg, #7c5cff, #ff7ab6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: block;
    }

    /* Gradient Bordered Card Style for main output (Blended Lyric) */
    div[data-testid="stVerticalBlock"] > div:has(div.stAlert) {
        background: #ffffff;
        border-radius: 16px;
        padding: 1px;
        box-shadow: 0 10px 30px rgba(124, 92, 255, 0.1);
        background-image: linear-gradient(90deg, #7c5cff, #ff7ab6);
    }

    /* Inner box for the gradient border effect */
    div[data-testid="stVerticalBlock"] > div:has(div.stAlert) > div > div > div.stAlert {
        background: white !important;
        border: none !important;
        border-radius: 15px !important;
        padding: 15px !important;
    }

    /* Style for the Blended Lyric Preview text inside st.info */
    div[data-testid="stVerticalBlock"] > div:has(div.stAlert) .stAlert strong {
        color: #7c5cff; 
    }

    /* Style for the Translation output columns (simple white card with soft shadow) */
    .st-emotion-cache-1r6ipbh { 
        background: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f5;
    }

    /* Buttons */
    div.stButton > button {
        background: linear-gradient(90deg, #7c5cff, #ff7ab6);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 700;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(124,92,255,0.16);
    }

    /* small muted text */
    .muted {
        color:#6b7280; font-size:13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div style="text-align:center;"><div class="main-header">🎛️ Melosphere — Polyglot Lyric Blending</div><div class="sub-header">Rhythmic translation & polyglot blending — enhanced UI</div></div>', unsafe_allow_html=True)

# ------------------------
# Logging (sidebar) - NO LOGIC CHANGE
# ------------------------
if "melosphere_logs" not in st.session_state:
    st.session_state["melosphere_logs"] = ""

def log(msg: str):
    st.session_state["melosphere_logs"] += msg + "\n"

# ------------------------
# Google Cloud Translate Setup - NO LOGIC CHANGE
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
        return "⚠️ Translation client not initialized. Check your credentials in Streamlit secrets."
    try:
        result = translate_client.translate(text, target_language=target_lang)
        return result.get("translatedText", "")
    except Exception as e:
        log(f"⚠️ Translation error for {target_lang}: {e}")
        return f"Error during translation: {e}"

# ------------------------
# Rhymes & Syllable helpers - NO LOGIC CHANGE
# ------------------------
def get_rhymes(word):
    try:
        response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10', timeout=6)
        if response.status_code == 200:
            return [item['word'] for item in response.json()]
    except Exception:
        pass
    return []

def clean_text(text):
    if text is None:
        return ""
    t = str(text)
    t = t.replace("“", '"').replace("”", '"').replace("—", "-").replace("–", "-")
    t = t.strip()
    return t

def count_syllables_english(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        try:
            return pronouncing.syllable_count(phones[0])
        except Exception:
            return sum(1 for ch in word.lower() if ch in 'aeiou')
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
# Smart filler insertion (deterministic) - NO LOGIC CHANGE
# ------------------------
_FILLERS = ["oh", "la", "yeah", "na", "hey", "mmm"]

def _build_fillers(diff, max_fillers=3, seed_text=None):
    fillers = _FILLERS
    k = min(max_fillers, max(0, diff))
    if k == 0:
        return ""
    seed = 0
    if seed_text is not None:
        seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    rnd = random.Random(seed)
    if k <= len(fillers):
        chosen = rnd.sample(fillers, k)
    else:
        chosen = [rnd.choice(fillers) for _ in range(k)]
    return " ".join(chosen)

def insert_fillers_safely(translated_text, fillers_str):
    if not fillers_str:
        return translated_text
    t = translated_text.strip()
    m = re.search(r'([.!?])\s*$', t)
    if m:
        base = t[:m.start()].rstrip()
        punct = m.group(1)
        return f"{base}, {fillers_str}{punct}"
    else:
        last_comma = t.rfind(',')
        if last_comma != -1 and last_comma < len(t) - 1:
            return f"{t}, {fillers_str}"
        return f"{t}, {fillers_str}"

# ------------------------
# Rhythmic Translation Enhancement - NO LOGIC CHANGE
# ------------------------
def rhythmic_translation_enhancement(original, translated, max_fillers=3):
    orig_syll = count_syllables_general(original, "en")
    trans_syll_before = count_syllables_heuristic(translated)
    diff = orig_syll - trans_syll_before
    if diff <= 0:
        enhanced = translated.strip()
        trans_syll_after = trans_syll_before
    else:
        fillers_str = _build_fillers(diff, max_fillers=max_fillers, seed_text=translated + original if translated else original)
        enhanced = insert_fillers_safely(translated, fillers_str)
        trans_syll_after = count_syllables_heuristic(enhanced)
    enhanced = re.sub(r"\s+", " ", enhanced).strip()
    return enhanced, orig_syll, trans_syll_before, trans_syll_after, diff

# ------------------------
# Blending Strategies - NO LOGIC CHANGE
# ------------------------
def interleave_words(original, translations_by_lang):
    tokenized = [t.split() for t in translations_by_lang]
    max_len = max(len(t) for t in tokenized) if tokenized else 0
    blended_tokens = []
    for i in range(max_len):
        for tok_list in tokenized:
            if i < len(tok_list):
                tok = tok_list[i]
                if blended_tokens and tok.lower() == blended_tokens[-1].lower():
                    continue
                blended_tokens.append(tok)
    return " ".join(blended_tokens)

def phrase_swap(original, translations_by_lang):
    segments = []
    for t in translations_by_lang:
        words = t.split()
        seg_size = max(1, math.ceil(len(words) / 2))
        segments.append(words)
    if len(segments) == 1:
        return translations_by_lang[0]
    if len(segments) == 2:
        a, b = segments
        a_seg = a[:math.ceil(len(a) / 2)]
        b_seg = b[math.floor(len(b) / 2):]
        assembled = a_seg + b_seg
        out = []
        for w in assembled:
            if not out or w.lower() != out[-1].lower():
                out.append(w)
        return " ".join(out)
    assembled = []
    for idx, words in enumerate(segments):
        n = len(words)
        start = math.floor(idx * n / len(segments))
        end = math.floor((idx + 1) * n / len(segments))
        if start < end:
            assembled.extend(words[start:end])
        else:
            assembled.extend(words[: max(1, min(3, n))])
    out = []
    for w in assembled:
        if not out or w.lower() != out[-1].lower():
            out.append(w)
    return " ".join(out)

def last_word_swap(original, translations_by_lang):
    orig_words = original.strip().split()
    if not orig_words:
        return original
    for t in translations_by_lang:
        tw = t.strip().split()
        if tw:
            new_last = tw[-1]
            if new_last.lower() == orig_words[-1].lower() and len(tw) > 1:
                new_last = tw[-2]
            return " ".join(orig_words[:-1] + [new_last])
    return original

# ------------------------
# Utility - NO LOGIC CHANGE
# ------------------------
def remove_consecutive_duplicates(text):
    words = text.split()
    if not words:
        return ""
    out = [words[0]]
    for w in words[1:]:
        if w != out[-1]:
            out.append(w)
    return " ".join(out)

def syllable_dots(count, cap=40):
    dots = "● " * min(count, cap)
    if count > cap:
        dots += f"...(+{count-cap})"
    return dots.strip()

def plot_syllable_comparison(orig_syll, trans_before, trans_after, lang_name):
    categories = ["Original (en)", f"{lang_name} (clean)", f"{lang_name} (enhanced)"]
    values = [orig_syll, trans_before, trans_after]
    colors = []
    for v in values:
        diff = abs(v - orig_syll)
        colors.append("#2ecc71" if diff == 0 else "#f1c40f" if diff <= 2 else "#e74c3c")
    fig = go.Figure([go.Bar(x=categories, y=values, marker_color=colors, text=values, textposition="auto")])
    fig.update_layout(
        title=f"Syllable Count Comparison — {lang_name}",
        yaxis_title="Syllable count",
        height=360,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig

# ------------------------
# Pronunciation helpers - NO LOGIC CHANGE
# ------------------------
@st.cache_data(show_spinner=False)
def generate_tts_audio(text, lang_code):
    try:
        tts = gTTS(text=text, lang=lang_code)
        # Use io.BytesIO instead of tempfile for better Streamlit compatibility
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        audio_bytes = mp3_fp.read()
        b64 = base64.b64encode(audio_bytes).decode()
        return f'<audio controls src="data:audio/mp3;base64,{b64}"></audio>'
    except Exception as e:
        log(f"TTS generation failed for {lang_code}: {e}")
        return f"<i>Audio unavailable: {e}</i>"

def get_pronunciation(text, lang_code, simplified=False):
    lang_code = lang_code.lower()
    indic_langs = {
        'hi': ('hin-Deva', 'devanagari'),
        'ta': ('tam-Taml', 'tamil'),
        'te': ('tel-Telu', 'telugu'),
        'kn': ('kan-Knda', 'kannada'),
        'ml': ('mal-Mlym', 'malayalam'),
        'bn': ('ben-Beng', 'bengali'),
        'gu': ('guj-Gujr', 'gujarati'),
        'pa': ('pan-Guru', 'gurmukhi')
    }

    if lang_code in indic_langs:
        epi_code, script = indic_langs[lang_code]
        try:
            epi = epitran.Epitran(epi_code)
            ipa_text = epi.transliterate(text)
        except Exception:
            ipa_text = None
        if simplified:
            try:
                return transliterate(text, script, 'iast')
            except Exception:
                return text
        return ipa_text if ipa_text else transliterate(text, script, 'iast')

    # Heuristic for non-supported languages
    ipa = text
    ipa = ipa.replace("th", "θ").replace("sh", "ʃ").replace("ch", "tʃ").replace("ph", "f")
    ipa = ipa.replace("a", "ɑ").replace("e", "ɛ").replace("i", "i").replace("o", "ɔ").replace("u", "u")
    if simplified:
        return re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return ipa

# ------------------------
# Main App UI & Processing
# ------------------------
def main():
    st.title("")  # no duplicate title printed here (we use header above)

    # --- INPUT CONTROLS ---
    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("Enter your lyric line (English):", height=100, placeholder="e.g., You're my sunshine 🌞")
    with col2:
        available_languages = {
            "Spanish": "es", "Kannada": "kn", "Tamil": "ta", "Malayalam": "ml", "Hindi": "hi",
            "Telugu": "te", "Japanese": "ja", "French": "fr", "Portuguese": "pt",
            "German": "de", "Korean": "ko"
        }
        selected = st.multiselect("Select 2+ target languages:", list(available_languages.keys()), default=["Spanish", "Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])
        # Removed all toggles and kept only the logic to drive the code
        enhance_rhythm = True # Defaulted to True as it was the default and one of the core features

    if not lyric_line or not selected:
        st.info("Enter a lyric and select at least one target language to begin.")
        with st.sidebar:
            st.subheader("Logs")
            st.text_area("Logs", value=st.session_state.get("melosphere_logs", ""), height=300)
        return

    # --- PROCESSING (NO LOGIC CHANGE) ---
    lyric_line_clean = clean_text(lyric_line)
    tgt_codes = [available_languages[l] for l in selected]
    translations_clean, translations_enhanced, overall_stats = {}, {}, {}

    def translate_and_enhance(lang_name, code):
        trans = translate_text(lyric_line_clean, code)
        # Using fixed max_fillers=3 as per original logic
        enhanced, orig_syll, trans_before, trans_after, diff = \
            rhythmic_translation_enhancement(lyric_line_clean, trans, max_fillers=3)
        return (lang_name, code, trans, enhanced, orig_syll, trans_before, trans_after, diff)

    with ThreadPoolExecutor(max_workers=min(8, len(tgt_codes))) as executor:
        futures = [executor.submit(translate_and_enhance, lang_name, code) for lang_name, code in zip(selected, tgt_codes)]
        for fut in as_completed(futures):
            try:
                lang_name, code, trans, enhanced, orig_syll, trans_before, trans_after, diff = fut.result()
                translations_clean[lang_name] = trans
                translations_enhanced[lang_name] = enhanced
                overall_stats[lang_name] = {
                    "orig_syll": orig_syll,
                    "trans_before": trans_before,
                    "trans_after": trans_after,
                    "diff": diff,
                    "code": code
                }
                log(f"Translated: {lang_name} ({code}) — before:{trans_before}, after:{trans_after}, diff:{diff}")
            except Exception as e:
                log(f"Translation future failed: {e}")

    translations_list_for_blend = [translations_enhanced[name] for name in selected]
    if mode == "Interleave Words":
        blended = interleave_words(lyric_line_clean, translations_list_for_blend)
    elif mode == "Phrase Swap":
        blended = phrase_swap(lyric_line_clean, translations_list_for_blend)
    else:
        blended = last_word_swap(lyric_line_clean, translations_list_for_blend)
    blended = remove_consecutive_duplicates(blended)
    # --- END PROCESSING ---

    # --- TABBED UI OUTPUTS ---
    tab_blend, tab_trans, tab_pron, tab_chart = st.tabs(
        ["🎵 Blended Lyric", "📝 Translations & Rhythm", "🎙️ Pronunciation Guide", "📊 Syllable Charts"]
    )

    # 1. BLENDED LYRIC TAB
    with tab_blend:
        st.markdown('<span class="output-header">Final Blended Lyric</span>', unsafe_allow_html=True)
        st.info(f"**Blended lyric preview ({mode}):**\n{blended}")

        # Audio for the blended line
        st.markdown(f"**Listen to the Blended Line (First selected language: {selected[0]})**")
        first_lang_code = available_languages[selected[0]]
        st.markdown(generate_tts_audio(blended, first_lang_code), unsafe_allow_html=True)


    # 2. TRANSLATIONS & RHYTHM TAB
    with tab_trans:
        st.markdown('<span class="output-header">Detailed Translations and Rhythmic Analysis</span>', unsafe_allow_html=True)
        trans_cols = st.columns(len(selected))
        for col, lang_name in zip(trans_cols, selected):
            with col:
                code = available_languages[lang_name]
                stats = overall_stats.get(lang_name, {})

                # Custom box style applied via CSS for this section
                st.markdown(f"**{lang_name} ({code})**")
                st.write(translations_clean.get(lang_name, ""))

                # Syllable/Rhythm info
                st.caption(f"**Rhythmically Enhanced:** {translations_enhanced.get(lang_name, '')}")
                syllable_text = f"Syllables: **Original:** {stats.get('orig_syll')}, **Clean:** {stats.get('trans_before')}, **Enhanced:** {stats.get('trans_after')}"
                st.caption(syllable_text)

    # 3. PRONUNCIATION GUIDE TAB
    with tab_pron:
        st.markdown('<span class="output-header">Phonetic Guide and Audio Examples</span>', unsafe_allow_html=True)
        # Retained a single checkbox for phonetic style choice
        show_simple = st.checkbox("Show Simplified Transliteration (e.g., IAST) instead of IPA", value=False)

        for lang_name in selected:
            code = available_languages[lang_name]
            text = translations_clean[lang_name]

            st.markdown("---")
            st.markdown(f"#### {lang_name} ({code})")

            # Pronunciation
            pron = get_pronunciation(text, code, simplified=show_simple)
            st.markdown(f"**{'Simplified' if show_simple else 'IPA/Extended'} Transliteration:**")
            if isinstance(pron, str):
                st.markdown(f'```\n{pron}\n```')
            else:
                st.write(pron)

            # Audio Player
            st.markdown(f"**Audio Playback:**")
            st.markdown(generate_tts_audio(text, code), unsafe_allow_html=True)

    # 4. SYLLABLE CHARTS TAB
    with tab_chart:
        st.markdown('<span class="output-header">Rhythm Match Visualization</span>', unsafe_allow_html=True)
        chart_cols = st.columns(len(selected))
        for col, lang_name in zip(chart_cols, selected):
            with col:
                stats = overall_stats[lang_name]
                fig = plot_syllable_comparison(stats["orig_syll"], stats["trans_before"], stats["trans_after"], lang_name)
                st.plotly_chart(fig, use_container_width=True)

    # Sidebar logs (remains unchanged)
    with st.sidebar:
        st.subheader("Logs")
        st.text_area("Runtime logs:", value=st.session_state.get("melosphere_logs", ""), height=300)

if __name__ == "__main__":
    main()
