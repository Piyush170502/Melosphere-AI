# app.py (updated)
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
import epitran
from indic_transliteration.sanscript import transliterate

# -------------------------
# Page styling (fonts, colors)
# -------------------------
st.set_page_config(page_title="Melosphere — Polyglot Lyric Blending", layout="wide")

# Inject Google Fonts and custom CSS for a stylish look
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
    <style>
      :root{
        --accent:#7c5cff;
        --accent-2:#ff7ab6;
        --muted:#6b7280;
        --card:#ffffff;
        --bg:#0f172a;
      }
      html, body, [class*="css"]  {
        font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
      }
      .header {
        background: linear-gradient(90deg, rgba(124,92,255,1) 0%, rgba(255,122,182,1) 100%);
        padding: 18px;
        border-radius: 12px;
        color: white;
        box-shadow: rgba(2,6,23,0.6) 0px 6px 24px;
      }
      .big-title{
        font-family: 'Playfair Display', serif;
        font-size: 28px;
        margin: 0;
      }
      .sub-title{ color: rgba(255,255,255,0.9); margin:0; font-size:13px}
      .lang-badge { display:inline-block; padding:6px 10px; border-radius:999px; color:white; font-weight:600; margin:2px; font-size:13px; }
      .card { background: white; padding:12px; border-radius:10px; box-shadow: 0 6px 18px rgba(2,6,23,0.06); }
      .blended { font-size:18px; line-height:1.6; padding:12px; background: #f7f7fb; border-radius:8px; border:1px solid #eee;}
      .small-muted { color: #6b7280; font-size:12px; }
      .lang-token { padding:2px 6px; border-radius:6px; color:white; margin:2px; display:inline-block; font-weight:600; }
      .syl-dot{ display:inline-block; margin-right:6px; color:#111827; font-size:14px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="header"><h1 class="big-title">🎛️ Melosphere — Polyglot Lyric Blending</h1><div class="sub-title">Rhythmic translations, polyglot blends & stylized previews</div></div>',
    unsafe_allow_html=True,
)

# -------------------------
# Utilities & configuration
# -------------------------
LANG_COLORS = {
    "Spanish": "#e74c3c",
    "Hindi": "#f39c12",
    "Kannada": "#9b59b6",
    "Tamil": "#16a085",
    "Malayalam": "#2ecc71",
    "Telugu": "#3498db",
    "Japanese": "#f1c40f",
    "French": "#9b9bff",
    "Portuguese": "#ff7ab6",
    "German": "#7f8c8d",
    "Korean": "#34495e",
}

AVAILABLE_LANGUAGES = {
    "Spanish": "es", "Kannada": "kn", "Tamil": "ta", "Malayalam": "ml", "Hindi": "hi",
    "Telugu": "te", "Japanese": "ja", "French": "fr", "Portuguese": "pt",
    "German": "de", "Korean": "ko"
}

FILLERS_DEFAULT = ["oh", "la", "yeah", "na", "hey", "mmm"]

# -------------------------
# Logging UI
# -------------------------
if "logs" not in st.session_state:
    st.session_state["logs"] = ""

def append_log(s: str):
    st.session_state["logs"] += s + "\n"

# -------------------------
# Google Translate client
# -------------------------
@st.cache_resource
def get_translate_client():
    try:
        credentials_info = st.secrets["gcp_service_account"]
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = translate.Client(credentials=credentials)
        append_log("Google Translate client initialized.")
        return client
    except Exception as e:
        append_log(f"Translate init failed: {e}")
        return None

translate_client = get_translate_client()

def translate_text(text, target_lang):
    if not translate_client:
        return "⚠️ Translation client not initialized."
    try:
        result = translate_client.translate(text, target_language=target_lang)
        return result.get("translatedText", "")
    except Exception as e:
        append_log(f"Translation error for {target_lang}: {e}")
        return f"Error: {e}"

# -------------------------
# Text cleaning & syllable counter (merged)
# -------------------------
VOWELS = "aeiouáàâäãåāéèêëēíìîïīóòôöõōúùûüūy"

def clean_text(text: str) -> str:
    if not text:
        return ""
    t = str(text)
    # Normalize punctuation but keep sentence-final punctuation
    t = t.replace("—", "-").replace("–", "-")
    t = re.sub(r"[\"“”‘’]+", "", t)
    t = t.strip()
    return t

def syllables_heuristic_word(word: str) -> int:
    lw = re.sub(r"[^a-záàâäãåāéèêëēíìîïīóòôöõōúùûüūy]", "", word.lower())
    if not lw:
        return 0
    groups = 0
    prev_v = False
    for ch in lw:
        is_v = ch in VOWELS
        if is_v and not prev_v:
            groups += 1
        prev_v = is_v
    return groups if groups > 0 else 1

def count_syllables_general(text, lang_code="en"):
    text = clean_text(text)
    if not text:
        return 0
    words = [w for w in re.split(r"\s+", text) if w.strip()]
    if lang_code.startswith("en"):
        total = 0
        for w in words:
            phones = pronouncing.phones_for_word(w.lower())
            if phones:
                try:
                    total += pronouncing.syllable_count(phones[0])
                except Exception:
                    total += syllables_heuristic_word(w)
            else:
                total += syllables_heuristic_word(w)
        return total
    else:
        return sum(syllables_heuristic_word(w) for w in words)

# -------------------------
# Deterministic fillers
# -------------------------
def deterministic_fillers(diff, seed, max_fillers=3):
    k = min(max_fillers, max(0, diff))
    if k == 0:
        return ""
    rng = random.Random(abs(hash(seed)) % (10**9))
    if k <= len(FILLERS_DEFAULT):
        chosen = rng.sample(FILLERS_DEFAULT, k)
    else:
        chosen = [rng.choice(FILLERS_DEFAULT) for _ in range(k)]
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

def rhythmic_translation_enhancement(original, translated, max_fillers=3):
    orig_syll = count_syllables_general(original, "en")
    trans_before = count_syllables_general(translated, "xx")
    diff = orig_syll - trans_before
    if diff <= 0:
        enhanced = translated.strip()
    else:
        fillers = deterministic_fillers(diff, original + translated, max_fillers=max_fillers)
        enhanced = insert_fillers_safely(translated, fillers)
    trans_after = count_syllables_general(enhanced, "xx")
    return enhanced, orig_syll, trans_before, trans_after, diff

# -------------------------
# Improved blending functions
# -------------------------
def interleave_words_safe(translations_list):
    """
    Interleave tokens from translations_list but avoid repeating same token consecutively.
    Also shorten extremely long lists by limiting max tokens.
    """
    tokenized = [t.split() for t in translations_list]
    max_len = max((len(t) for t in tokenized), default=0)
    blended = []
    for i in range(max_len):
        for tok_list in tokenized:
            if i < len(tok_list):
                tok = tok_list[i]
                if not tok:
                    continue
                # avoid consecutive duplicates
                if blended and tok.lower() == blended[-1].lower():
                    continue
                blended.append(tok)
                # safety cap
                if len(blended) > 120:
                    break
        if len(blended) > 120:
            break
    return " ".join(blended)

def phrase_swap_improved(translations_list):
    """
    Take controlled segments from each translation, avoid repeating identical sequences,
    and prefer central slices instead of naïve halves.
    """
    segments = [t.split() for t in translations_list]
    if not segments:
        return ""
    if len(segments) == 1:
        return translations_list[0]
    # For two segments: take first 40% of A + last 50% of B (avoids repeats)
    if len(segments) == 2:
        a, b = segments
        a_len, b_len = len(a), len(b)
        a_take = max(1, math.floor(a_len * 0.4))
        b_take = max(1, math.ceil(b_len * 0.5))
        result = a[:a_take] + b[-b_take:]
        # remove immediate duplicates
        out = []
        for w in result:
            if not out or w.lower() != out[-1].lower():
                out.append(w)
        return " ".join(out)
    # For many segments, extract a middle slice proportional to segment index
    assembled = []
    for idx, words in enumerate(segments):
        n = len(words)
        if n == 0:
            continue
        mid = n // 2
        span = max(1, min(3, n // (len(segments) + 1)))
        start = max(0, mid - span)
        end = min(n, mid + span)
        assembled.extend(words[start:end])
    # dedupe adjacent
    out = []
    for w in assembled:
        if not out or w.lower() != out[-1].lower():
            out.append(w)
    return " ".join(out)

def last_word_swap_safe(original, translations_list):
    orig_words = original.strip().split()
    if not orig_words:
        return original
    for t in translations_list:
        tw = [w for w in t.split() if w.strip()]
        if tw:
            # ensure the last word is not identical to the original last word
            if tw[-1].lower() == orig_words[-1].lower() and len(tw) > 1:
                last = tw[-2]
            else:
                last = tw[-1]
            return " ".join(orig_words[:-1] + [last])
    return original

def remove_consecutive_duplicates(text):
    words = text.split()
    if not words:
        return ""
    out = [words[0]]
    for w in words[1:]:
        if w.lower() != out[-1].lower():
            out.append(w)
    return " ".join(out)

# -------------------------
# Pronunciation improvements
# -------------------------
EPITRAN_MAP = {
    "hi": "hin-Deva", "ta": "tam-Taml", "te": "tel-Telu", "kn": "kan-Knda",
    "ml": "mal-Mlym", "bn": "ben-Beng", "gu": "guj-Gujr", "pa": "pan-Guru",
    "es": "spa-Latn", "fr": "fra-Latn", "pt": "por-Latn", "de": "deu-Latn",
    "ja": "jpn-Jpan", "ko": "kor-Kore"
}

def get_pronunciation(text, lang_code, simplified=False):
    """
    Try epitran transliteration first for supported languages.
    For Japanese/others where epitran may behave poorly, fallback to a simple transliteration heuristic.
    """
    if not text:
        return ""
    code = lang_code.lower()
    epi_code = EPITRAN_MAP.get(code)
    if epi_code:
        try:
            epi = epitran.Epitran(epi_code)
            ipa = epi.transliterate(text)
            if ipa and len(ipa.strip()) > 0:
                if simplified:
                    # simple romanization fallback: return ascii-only subset
                    return re.sub(r"[^a-zA-Z0-9\s]", "", ipa)
                return ipa
        except Exception:
            # epitran can throw for some langs; we'll fallback
            pass
    # fallback heuristics:
    # - For Japanese: try to convert katakana/hiragana to romaji via basic unicode ranges (rough)
    if code == "ja":
        # basic conversion: map hiragana/katakana to romaji for common characters (very small heuristic)
        # NOTE: full proper conversion requires pykakasi or similar; this is a best-effort fallback.
        try:
            # quick naive replacement for long vowels and simple kana (very small subset)
            s = text
            s = re.sub('[ぁあ]', 'a', s)
            s = re.sub('[ぃい]', 'i', s)
            s = re.sub('[ぅう]', 'u', s)
            s = re.sub('[ぇえ]', 'e', s)
            s = re.sub('[ぉお]', 'o', s)
            # remove non-ascii
            s = re.sub(r'[^\x00-\x7F]+', '', s)
            if s.strip():
                return s
        except Exception:
            pass
    # generic fallback: strip diacritics-ish and show original with minimal cleanup
    if simplified:
        return re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return text

# -------------------------
# Cached TTS
# -------------------------
@st.cache_data(show_spinner=False)
def generate_tts_audio_cached(text, lang_code):
    try:
        tts = gTTS(text=text, lang=lang_code)
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_path.name)
        with open(temp_path.name, "rb") as f:
            audio_bytes = f.read()
        b64 = base64.b64encode(audio_bytes).decode()
        return f'<audio controls src="data:audio/mp3;base64,{b64}"></audio>'
    except Exception as e:
        append_log(f"TTS generation failed for {lang_code}: {e}")
        return f"<i>Audio unavailable: {e}</i>"

# -------------------------
# Translation orchestration (concurrent)
# -------------------------
def translate_all(lyric, selected_langs, enhance_rhythm=True, max_fillers=3):
    """
    selected_langs: dict of {lang_name: lang_code}
    returns: translations dict and stats dict
    """
    translations = {}
    stats = {}
    # Use ThreadPoolExecutor for I/O-bound translate requests
    with ThreadPoolExecutor(max_workers=min(8, len(selected_langs) or 1)) as executor:
        future_map = {}
        for lang_name, code in selected_langs.items():
            future = executor.submit(translate_text, lyric, code)
            future_map[future] = (lang_name, code)
        for fut in as_completed(future_map):
            lang_name, code = future_map[fut]
            try:
                txt = fut.result()
            except Exception as e:
                txt = f"Error: {e}"
                append_log(f"Translation task failed for {lang_name}: {e}")
            if enhance_rhythm:
                enhanced, orig_syll, before, after, diff = rhythmic_translation_enhancement(lyric, txt, max_fillers=max_fillers)
            else:
                enhanced = txt
                orig_syll = count_syllables_general(lyric, "en")
                before = count_syllables_general(txt, code)
                after = before
                diff = orig_syll - before
            translations[lang_name] = {"clean": txt, "enhanced": enhanced, "code": code}
            stats[lang_name] = {"orig": orig_syll, "before": before, "after": after, "diff": diff}
    return translations, stats

# -------------------------
# UI and main
# -------------------------
def language_badge(name):
    col = LANG_COLORS.get(name, "#7c5cff")
    return f'<span class="lang-badge" style="background:{col}">{name}</span>'

def colored_token(word, lang):
    color = LANG_COLORS.get(lang, "#7c5cff")
    safe = re.sub(r'[^a-zA-Z0-9\u00C0-\u024F\u3040-\u30FF\u3000-\u303F\u4E00-\u9FFF]', '', word)
    return f'<span class="lang-token" style="background:{color}">{safe}</span>'

def plot_syllable_chart(stats, lang_name):
    orig = stats["orig"]
    before = stats["before"]
    after = stats["after"]
    categories = ["Original", f"{lang_name} (clean)", f"{lang_name} (enhanced)"]
    values = [orig, before, after]
    colors = ["#2ecc71" if abs(v - orig) == 0 else "#f1c40f" if abs(v - orig) <= 2 else "#e74c3c" for v in values]
    fig = go.Figure([go.Bar(x=categories, y=values, marker_color=colors, text=values, textposition="auto")])
    fig.update_layout(title=f"Syllable Comparison — {lang_name}", yaxis_title="Syllable count", height=360)
    return fig

def main():
    st.sidebar.markdown("<div class='card'><strong>Controls</strong></div>", unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("### Settings")
        default_langs = ["Spanish", "Hindi"]
        selected = st.multiselect("Select 2+ target languages:", list(AVAILABLE_LANGUAGES.keys()), default=default_langs)
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])
        enhance_rhythm = st.checkbox("✨ Rhythmic Enhancement", value=True)
        max_fillers = st.slider("Max fillers (if needed)", 0, 6, 3)
        show_chart = st.checkbox("Show syllable charts", value=True)
        show_simple_pron = st.checkbox("Show simplified pronunciation", value=False)
        show_logs = st.checkbox("Show logs in sidebar", value=True)

    col_main, col_right = st.columns([3, 1])
    with col_main:
        lyric = st.text_area("Enter your lyric line (English):", height=90, placeholder="e.g. I can hear the heartbeat of the city")
        st.markdown("<div class='small-muted'>Tip: try short lyrical phrases for best blends.</div>", unsafe_allow_html=True)
        st.markdown("---")
        if not lyric or not selected:
            st.info("Enter a lyric and select at least one language.")
            return

        # prepare languages dict
        chosen_langs = {lang: AVAILABLE_LANGUAGES[lang] for lang in selected}

        # perform translations concurrently
        translations, stats = translate_all(lyric, chosen_langs, enhance_rhythm, max_fillers=max_fillers)

        # render Translations cards
        st.markdown("<h3 style='margin-top:8px'>🌐 Translations</h3>", unsafe_allow_html=True)
        tcols = st.columns(len(selected))
        for col, lang in zip(tcols, selected):
            with col:
                code = translations[lang]["code"]
                st.markdown(f"<div class='card'><div style='display:flex;justify-content:space-between;align-items:center;'><div><strong>{lang} — <span style='font-weight:600;color:#111;'>{code}</span></strong></div><div>{language_badge(lang)}</div></div><div style='margin-top:8px'><div style='font-size:15px'>{translations[lang]['clean']}</div><div class='small-muted'>Enhanced: {translations[lang]['enhanced']}</div></div></div>", unsafe_allow_html=True)

        st.markdown("<h3 style='margin-top:18px'>🎛️ Blended Output</h3>", unsafe_allow_html=True)
        enhanced_list = [translations[lang]["enhanced"] for lang in selected]
        if mode == "Interleave Words":
            blended = interleave_words_safe(enhanced_list)
        elif mode == "Phrase Swap":
            blended = phrase_swap_improved(enhanced_list)
        else:
            blended = last_word_swap_safe(lyric, enhanced_list)
        blended = remove_consecutive_duplicates(blended)

        # colorize blended output by cycling language tokens where possible
        # simple approach: split blended into words and try to map tokens back to languages using exact matches
        tokens = blended.split()
        colored_tokens = []
        for tok in tokens:
            assigned = None
            for lang in selected:
                # if token appears in enhanced version of this language (case-insensitive), assign its color
                if re.search(r'\b' + re.escape(tok) + r'\b', translations[lang]["enhanced"], re.IGNORECASE):
                    assigned = lang
                    break
            if assigned:
                colored_tokens.append(colored_token(tok, assigned))
            else:
                # fallback neutral token
                colored_tokens.append(f'<span style="padding:2px 6px;border-radius:6px;background:#d1d5db;color:#111;margin:2px;display:inline-block;">{tok}</span>')
        blended_html = " ".join(colored_tokens)
        st.markdown(f"<div class='blended'>{blended_html}</div>", unsafe_allow_html=True)

        st.markdown("<h3 style='margin-top:18px'>🔊 Pronunciation & Audio</h3>", unsafe_allow_html=True)
        for lang in selected:
            code = translations[lang]["code"]
            txt = translations[lang]["clean"]
            pron = get_pronunciation(txt, code, simplified=show_simple_pron)
            st.markdown(f"**{lang} ({code})**")
            st.markdown(f"<div class='small-muted'>Pronunciation: {pron}</div>", unsafe_allow_html=True)
            audio_html = generate_tts_audio_cached(txt, code)
            st.markdown(audio_html, unsafe_allow_html=True)
            st.markdown("---")

        if show_chart:
            st.markdown("<h3 style='margin-top:18px'>📈 Syllable Comparison</h3>", unsafe_allow_html=True)
            # Render charts in tabs to avoid heavy redraw
            chart_tabs = st.tabs(selected)
            for tab, lang in zip(chart_tabs, selected):
                with tab:
                    fig = plot_syllable_chart(stats[lang], lang)
                    st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # show logs and quick controls
        st.markdown("<div class='card'><strong>Quick Actions</strong></div>", unsafe_allow_html=True)
        if st.button("Try example: 'I feel the sun inside me'"):
            # to programmatically set text_area we must rerun with session state
            st.session_state["example_lyric"] = "I feel the sun inside me, burning bright."
            st.experimental_rerun()
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if show_logs:
            st.markdown("<div class='card'><strong>Logs</strong></div>", unsafe_allow_html=True)
            st.text_area("Logs", value=st.session_state.get("logs", ""), height=300)

if __name__ == "__main__":
    main()
