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

# ============================================================
# 🧠 SETUP & INITIALIZATION
# ============================================================

st.set_page_config(page_title="Melosphere — Polyglot Lyric Blending", layout="wide")

# Sidebar log area
if "logs" not in st.session_state:
    st.session_state.logs = ""
def log(msg: str):
    st.session_state.logs += f"• {msg}\n"

# ------------------------
# Google Cloud Translate Setup
# ------------------------
@st.cache_resource
def get_translate_client():
    try:
        credentials_info = st.secrets["gcp_service_account"]
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = translate.Client(credentials=credentials)
        log("✅ Google Translate API initialized.")
        return client
    except Exception as e:
        st.error(f"Google Translate initialization failed: {e}")
        return None

translate_client = get_translate_client()

def translate_text(text, target_lang):
    if not translate_client:
        return "⚠️ Translation client not initialized."
    try:
        result = translate_client.translate(text, target_language=target_lang)
        return result["translatedText"]
    except Exception as e:
        log(f"⚠️ Translation failed for {target_lang}: {e}")
        return f"Error: {e}"

# ============================================================
# 🎵 RHYTHM & SYLLABLE UTILITIES
# ============================================================

def clean_text(text: str) -> str:
    """Remove punctuation and normalize spacing."""
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def count_syllables_english(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for ch in word.lower() if ch in 'aeiou')

def count_syllables(text, lang_code="en"):
    """Generic syllable counter with heuristic fallback."""
    if not text or not isinstance(text, str):
        return 0
    text = clean_text(text)
    words = text.split()
    if lang_code.startswith("en"):
        return sum(count_syllables_english(w) for w in words)
    syllables = 0
    vowels = "aeiouáàâäãåāéèêëēíìîïīóòôöõōúùûüūy"
    for w in words:
        prev = False
        count = 0
        for ch in w.lower():
            v = ch in vowels
            if v and not prev:
                count += 1
            prev = v
        syllables += count or 1
    return syllables

def _deterministic_fillers(diff, base_text, max_fillers=3):
    """Stable filler selection using text hash for reproducibility."""
    fillers = ["oh", "la", "yeah", "na", "hey", "mmm"]
    k = min(max_fillers, max(0, diff))
    rng = random.Random(abs(hash(base_text)) % (10**8))
    chosen = rng.sample(fillers, k) if k <= len(fillers) else [rng.choice(fillers) for _ in range(k)]
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
    orig_syll = count_syllables(original, "en")
    trans_syll_before = count_syllables(translated)
    diff = orig_syll - trans_syll_before
    if diff <= 0:
        enhanced = translated.strip()
    else:
        fillers_str = _deterministic_fillers(diff, original, max_fillers)
        enhanced = insert_fillers_safely(translated, fillers_str)
    trans_syll_after = count_syllables(enhanced)
    return enhanced.strip(), orig_syll, trans_syll_before, trans_syll_after, diff

# ============================================================
# 🌐 TRANSLATION (Concurrent)
# ============================================================

def get_all_translations(text, langs, enhance_rhythm=True):
    results = {}
    stats = {}
    with ThreadPoolExecutor() as executor:
        future_to_lang = {executor.submit(translate_text, text, code): (lang, code) for lang, code in langs.items()}
        for future in as_completed(future_to_lang):
            lang_name, code = future_to_lang[future]
            try:
                trans = future.result()
                if enhance_rhythm:
                    enhanced, orig_syll, before, after, diff = rhythmic_translation_enhancement(text, trans)
                else:
                    enhanced = trans
                    orig_syll = count_syllables(text, "en")
                    before = count_syllables(trans, code)
                    after = before
                    diff = orig_syll - before
                results[lang_name] = {"clean": trans, "enhanced": enhanced}
                stats[lang_name] = {"orig": orig_syll, "before": before, "after": after, "diff": diff}
            except Exception as e:
                log(f"❌ Translation thread failed for {lang_name}: {e}")
    return results, stats

# ============================================================
# 🧬 BLENDING UTILITIES
# ============================================================

def interleave_words(translations):
    tokenized = [t.split() for t in translations]
    max_len = max(len(t) for t in tokenized)
    blended = []
    for i in range(max_len):
        for toks in tokenized:
            if i < len(toks):
                blended.append(toks[i])
    return " ".join(blended)

def phrase_swap(translations):
    segs = [t.split() for t in translations]
    if len(segs) == 1:
        return translations[0]
    if len(segs) == 2:
        a, b = segs
        return " ".join(a[:len(a)//2] + b[len(b)//2:])
    result = []
    for idx, words in enumerate(segs):
        start = math.floor(idx * len(words) / len(segs))
        end = math.floor((idx + 1) * len(words) / len(segs))
        result.extend(words[start:end] or words[:2])
    return " ".join(result)

def last_word_swap(original, translations):
    orig_words = original.strip().split()
    for t in translations:
        tw = t.strip().split()
        if tw:
            return " ".join(orig_words[:-1] + [tw[-1]])
    return original

def remove_consecutive_duplicates(text):
    words = text.split()
    return " ".join([w for i, w in enumerate(words) if i == 0 or w != words[i - 1]])

# ============================================================
# 🔊 AUDIO & PRONUNCIATION
# ============================================================

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
        log(f"TTS failed for {lang_code}: {e}")
        return f"<i>Audio unavailable: {e}</i>"

def get_pronunciation(text, lang_code, simplified=False):
    lang_code = lang_code.lower()
    indic_langs = {
        'hi': ('hin-Deva', 'devanagari'), 'ta': ('tam-Taml', 'tamil'),
        'te': ('tel-Telu', 'telugu'), 'kn': ('kan-Knda', 'kannada'),
        'ml': ('mal-Mlym', 'malayalam'), 'bn': ('ben-Beng', 'bengali'),
        'gu': ('guj-Gujr', 'gujarati'), 'pa': ('pan-Guru', 'gurmukhi')
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
        return ipa_text or transliterate(text, script, 'iast')
    ipa = text.lower().replace("th", "θ").replace("sh", "ʃ").replace("ch", "tʃ").replace("ph", "f")
    if simplified:
        ipa = re.sub(r"[^a-z\s]", "", ipa)
    return ipa

# ============================================================
# 📊 VISUALIZATION
# ============================================================

def plot_syllable_comparison(orig_syll, trans_before, trans_after, lang_name):
    categories = ["Original", f"{lang_name} (clean)", f"{lang_name} (enhanced)"]
    values = [orig_syll, trans_before, trans_after]
    colors = ["#2ecc71" if abs(v - orig_syll) == 0 else "#f1c40f" if abs(v - orig_syll) <= 2 else "#e74c3c" for v in values]
    fig = go.Figure([go.Bar(x=categories, y=values, marker_color=colors, text=values, textposition="auto")])
    fig.update_layout(title=f"Syllable Count Comparison — {lang_name}", yaxis_title="Syllables")
    return fig

# ============================================================
# 🎛️ MAIN APP
# ============================================================

def main():
    st.title("🎶 Melosphere — Polyglot Lyric Blending (Enhanced)")

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
        enhance_rhythm = st.checkbox("✨ Rhythmic Enhancement", value=True)
        show_plot = st.checkbox("📊 Show syllable chart", value=False)
        show_simple_pron = st.checkbox("Show simplified pronunciation", value=False)

    if not lyric_line or not selected:
        st.info("Enter a lyric and select at least one language to begin.")
        return

    chosen_langs = {lang: available_languages[lang] for lang in selected}
    translations, stats = get_all_translations(lyric_line, chosen_langs, enhance_rhythm)

    # Tabs for UI
    tab1, tab2, tab3, tab4 = st.tabs(["🌐 Translations", "🎛️ Blended Output", "🔊 Pronunciations", "📈 Charts"])

    with tab1:
        cols = st.columns(len(selected))
        for col, lang in zip(cols, selected):
            with col:
                st.markdown(f"**{lang} ({chosen_langs[lang]})**")
                st.write(translations[lang]["clean"])

    with tab2:
        enhanced_list = [translations[lang]["enhanced"] for lang in selected]
        if mode == "Interleave Words":
            blended = interleave_words(enhanced_list)
        elif mode == "Phrase Swap":
            blended = phrase_swap(enhanced_list)
        else:
            blended = last_word_swap(lyric_line, enhanced_list)
        blended = remove_consecutive_duplicates(blended)
        st.success(f"**Blended lyric:** {blended}")

    with tab3:
        for lang in selected:
            code = chosen_langs[lang]
            text = translations[lang]["clean"]
            pron = get_pronunciation(text, code, simplified=show_simple_pron)
            st.markdown(f"**{lang} Pronunciation:**")
            st.markdown(pron)
            st.markdown(generate_tts_audio(text, code), unsafe_allow_html=True)

    with tab4:
        if show_plot:
            for lang in selected:
                s = stats[lang]
                fig = plot_syllable_comparison(s["orig"], s["before"], s["after"], lang)
                st.plotly_chart(fig, use_container_width=True)

    with st.sidebar:
        st.subheader("🧾 Logs")
        st.text_area("Runtime logs:", st.session_state.logs, height=200)

if __name__ == "__main__":
    main()
