# app.py — Enhanced (non-invasive) version for Streamlit Cloud
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

# -------------------- UI STYLING --------------------
st.markdown("""
    <style>
    /* Gradient animated background */
    body {
        background: linear-gradient(135deg, #e0f7fa, #f1f8e9, #fff3e0);
        background-size: 400% 400%;
        animation: gradientShift 20s ease infinite;
    }

    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Header gradient animation */
    .main-header {
        text-align: center;
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ff6f61, #ffcc80, #64b5f6, #81c784);
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: hueRotate 10s linear infinite;
        margin-bottom: 0.8rem;
    }

    @keyframes hueRotate {
        0% { filter: hue-rotate(0deg); }
        100% { filter: hue-rotate(360deg); }
    }

    /* Subheader */
    .sub-header {
        text-align: center;
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 2rem;
    }

    /* Stylish input area */
    textarea {
        border: 2px solid #ddd !important;
        border-radius: 10px !important;
        transition: all 0.3s ease-in-out !important;
        box-shadow: none !important;
    }

    textarea:focus {
        outline: none !important;
        border-color: #64b5f6 !important;
        box-shadow: 0 0 10px rgba(100, 181, 246, 0.6) !important;
    }

    /* Streamlit button styling */
    div.stButton > button {
        background: linear-gradient(90deg, #81c784, #64b5f6);
        color: white;
        border-radius: 12px;
        font-weight: 600;
        padding: 0.6rem 1.4rem;
        border: none;
        transition: all 0.3s ease;
    }

    div.stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.2);
    }

    /* Hide toggles section entirely */
    div[data-testid="stCheckbox"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------- HEADER --------------------
st.markdown("""
    <h1 class="main-header">🎛️ Melosphere — Polyglot Lyric Blending</h1>
    <p class="sub-header">Rhythmic translation & polyglot blending — enhanced ✨</p>
""", unsafe_allow_html=True)

# Then continue with your existing app logic (text input, translation, charts, etc.)
lyrics_input = st.text_area(
    "🎤 Enter your lyrics:",
    placeholder="e.g., You're my sunshine 🌞 or write your own creative lines...",
    height=150
)

# ------------------------
# Page / styling
# ------------------------
st.set_page_config(page_title="Melosphere — Polyglot Blending", layout="wide")

st.markdown(
    """
    <style>
      .big-title { font-size: 26px; font-weight:700; margin:0; }
      .subtitle { color: #6b7280; margin:0; font-size:13px; }
      .card { background: white; padding:12px; border-radius:10px; box-shadow: 0 6px 18px rgba(2,6,23,0.06); }
      .lang-badge { display:inline-block; padding:6px 10px; border-radius:999px; color:white; font-weight:600; margin:2px; font-size:13px; }
      .blended { font-size:18px; line-height:1.6; padding:12px; background: #f7f7fb; border-radius:8px; border:1px solid #eee;}
      .small-muted { color: #6b7280; font-size:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div style="display:flex;justify-content:space-between;align-items:center"><div><div class="big-title">🎛️ Melosphere — Polyglot Lyric Blending</div><div class="subtitle">Rhythmic translation & polyglot blending — enhanced</div></div></div>', unsafe_allow_html=True)

# ------------------------
# Logging (sidebar)
# ------------------------
if "melosphere_logs" not in st.session_state:
    st.session_state["melosphere_logs"] = ""

def log(msg: str):
    st.session_state["melosphere_logs"] += msg + "\n"

# ------------------------
# Google Cloud Translate Setup
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
# Rhymes & Syllable helpers (kept behavior)
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
    """Centralized cleaning used throughout."""
    if text is None:
        return ""
    t = str(text)
    # keep punctuation for final-punct detection, but normalize quotes
    t = t.replace("“", '"').replace("”", '"').replace("—", "-").replace("–", "-")
    t = t.strip()
    return t

def count_syllables_english(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        try:
            return pronouncing.syllable_count(phones[0])
        except Exception:
            # fallback to heuristic
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
# Smart filler insertion (deterministic)
# ------------------------
_FILLERS = ["oh", "la", "yeah", "na", "hey", "mmm"]

def _build_fillers(diff, max_fillers=3, seed_text=None):
    fillers = _FILLERS
    k = min(max_fillers, max(0, diff))
    if k == 0:
        return ""
    # deterministic sample based on SHA256 of seed_text (stable across reruns)
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
# Rhythmic Translation Enhancement (kept same interface)
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
# Blending Strategies (preserve original logic but avoid trivial repeats)
# ------------------------
def interleave_words(original, translations_by_lang):
    tokenized = [t.split() for t in translations_by_lang]
    max_len = max(len(t) for t in tokenized) if tokenized else 0
    blended_tokens = []
    for i in range(max_len):
        for tok_list in tokenized:
            if i < len(tok_list):
                tok = tok_list[i]
                # avoid immediate duplicate tokens
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
        # remove consecutive duplicates
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
    # dedupe adjacent
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
# Utility
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
    categories = ["Original", f"{lang_name} (clean)", f"{lang_name} (enhanced)"]
    values = [orig_syll, trans_before, trans_after]
    colors = []
    for v in values:
        diff = abs(v - orig_syll)
        colors.append("#2ecc71" if diff == 0 else "#f1c40f" if diff <= 2 else "#e74c3c")
    fig = go.Figure([go.Bar(x=categories, y=values, marker_color=colors, text=values, textposition="auto")])
    fig.update_layout(title=f"Syllable Count Comparison — {lang_name}", yaxis_title="Syllable count", height=360)
    return fig

# ------------------------
# Pronunciation helpers (restore original detailed logic)
# ------------------------
@st.cache_data(show_spinner=False)
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
                # transliterate to IAST (romanized) for easier reading
                return transliterate(text, script, 'iast')
            except Exception:
                # fallback to text if transliteration fails
                return text
        # Prefer ipa_text if produced, otherwise romanized IAST as fallback
        return ipa_text if ipa_text else transliterate(text, script, 'iast')

    # Non-indic fallback: approximate IPA by replacements
    ipa = text
    # Preserve original characters and make substitutions for a readable IPA-like approximation
    ipa = ipa.replace("th", "θ").replace("sh", "ʃ").replace("ch", "tʃ").replace("ph", "f")
    ipa = ipa.replace("a", "ɑ").replace("e", "ɛ").replace("i", "i").replace("o", "ɔ").replace("u", "u")
    if simplified:
        # simplified fallback: strip non-alphanum for readability
        return re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return ipa

# ------------------------
# Main App UI
# ------------------------
def main():
    st.title("🎛️ Melosphere — Polyglot Lyric Blending")

    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("Enter your lyric line (English):", height=80)
    with col2:
        available_languages = {
            "Spanish": "es", "Kannada": "kn", "Tamil": "ta", "Malayalam": "ml", "Hindi": "hi",
            "Telugu": "te", "Japanese": "ja", "French": "fr", "Portuguese": "pt",
            "German": "de", "Korean": "ko"
        }
        selected = st.multiselect("Select 2+ target languages:", list(available_languages.keys()), default=["Spanish", "Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])
        enhance_rhythm = st.checkbox("✨ Rhythmic Enhancement", value=True)
        fillers_in_blend_only = st.checkbox("Show fillers only in blended output", value=True)
        show_plot = st.checkbox("Show syllable comparison chart", value=False)
        show_dots = st.checkbox("Show syllable dots visual", value=False)
        show_syllables = st.checkbox("Show syllable hints / rhythm warnings", value=True)
        show_rhymes = st.checkbox("Show English rhymes for the last word", value=True)

    if not lyric_line or not selected:
        st.info("Enter a lyric and select at least one target language.")
        with st.sidebar:
            st.subheader("Logs")
            st.text_area("Logs", value=st.session_state.get("melosphere_logs", ""), height=300)
        return

    # Normalize input
    lyric_line_clean = clean_text(lyric_line)

    tgt_codes = [available_languages[l] for l in selected]
    translations_clean, translations_enhanced, overall_stats = {}, {}, {}

    # Concurrentize translations
    def translate_and_enhance(lang_name, code):
        trans = translate_text(lyric_line_clean, code)
        if enhance_rhythm:
            enhanced, orig_syll, trans_before, trans_after, diff = rhythmic_translation_enhancement(lyric_line_clean, trans)
        else:
            enhanced = trans
            orig_syll = count_syllables_general(lyric_line_clean, "en")
            trans_before = count_syllables_general(trans, code)
            trans_after = trans_before
            diff = orig_syll - trans_before
        return (lang_name, code, trans, enhanced, orig_syll, trans_before, trans_after, diff)

    # Use ThreadPoolExecutor to speed up translate calls
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

    # Translations UI
    st.subheader("Translations")
    trans_cols = st.columns(len(selected))
    for col, lang_name in zip(trans_cols, selected):
        with col:
            code = available_languages[lang_name]
            st.markdown(f"**{lang_name} ({code})**")
            st.write(translations_clean.get(lang_name, ""))
            if show_syllables:
                stats = overall_stats.get(lang_name, {})
                st.caption(f"Syllables — orig: {stats.get('orig_syll')}, clean: {stats.get('trans_before')}, enhanced: {stats.get('trans_after')}")

    # Blended output
    st.subheader("Blended Outputs")
    translations_list_for_blend = [translations_enhanced[name] for name in selected]
    if mode == "Interleave Words":
        blended = interleave_words(lyric_line_clean, translations_list_for_blend)
    elif mode == "Phrase Swap":
        blended = phrase_swap(lyric_line_clean, translations_list_for_blend)
    else:
        blended = last_word_swap(lyric_line_clean, translations_list_for_blend)

    blended = remove_consecutive_duplicates(blended)
    st.info(f"**Blended lyric preview:**\n{blended}")

    # Charts
    if show_plot:
        # ensure charts reflect latest overall_stats
        for lang_name in selected:
            stats = overall_stats[lang_name]
            fig = plot_syllable_comparison(stats["orig_syll"], stats["trans_before"], stats["trans_after"], lang_name)
            st.plotly_chart(fig, use_container_width=True)

    # Pronunciation Guide (restore original behavior)
    st.subheader("🎙️ Pronunciation Guide")
    show_simple = st.checkbox("See simplified style (default = IPA)", value=False, key="pron_simple")
    for lang_name in selected:
        code = available_languages[lang_name]
        text = translations_clean[lang_name]
        pron = get_pronunciation(text, code, simplified=show_simple)
        st.markdown(f"**{lang_name} pronunciation:**")
        # Ensure IPA/simplified shows as plain text (not mis-escaped)
        if isinstance(pron, str):
            st.markdown(pron)
        else:
            st.write(pron)
        st.markdown(generate_tts_audio(text, code), unsafe_allow_html=True)

    # Side logs
    with st.sidebar:
        st.subheader("Logs")
        st.text_area("Runtime logs:", value=st.session_state.get("melosphere_logs", ""), height=300)

if __name__ == "__main__":
    main()
