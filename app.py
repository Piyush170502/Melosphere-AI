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

# ------------------------
# Helper: Translation (Official Google API)
# ------------------------

def translate_text(text, target_lang):
    api_key = st.secrets.get("general", {}).get("GOOGLE_TRANSLATE_API_KEY", None)
    if not api_key:
        return "⚠️ Translation API key not found in Streamlit secrets. Please add it under [general] GOOGLE_TRANSLATE_API_KEY."
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {"q": text, "target": target_lang, "format": "text"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if "data" in data and "translations" in data["data"]:
            return data["data"]["translations"][0]["translatedText"]
        elif "error" in data:
            return f"API error: {data['error'].get('message','unknown')}"
        else:
            return f"Unexpected response: {data}"
    except Exception as e:
        return f"Error during translation: {e}"

# ------------------------
# Rhymes & Syllable helpers
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
# Smart filler insertion
# ------------------------

def _build_fillers(diff, max_fillers=3):
    fillers = ["oh", "la", "yeah", "na", "hey", "mmm"]
    k = min(max_fillers, max(0, diff))
    chosen = random.sample(fillers, k) if k <= len(fillers) else [random.choice(fillers) for _ in range(k)]
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
# Rhythmic Translation Enhancement
# ------------------------

def rhythmic_translation_enhancement(original, translated, max_fillers=3):
    orig_syll = count_syllables_general(original, "en")
    trans_syll_before = count_syllables_heuristic(translated)
    diff = orig_syll - trans_syll_before
    if diff <= 0:
        enhanced = translated.strip()
        trans_syll_after = trans_syll_before
    else:
        fillers_str = _build_fillers(diff, max_fillers=max_fillers)
        enhanced = insert_fillers_safely(translated, fillers_str)
        trans_syll_after = count_syllables_heuristic(enhanced)
    enhanced = re.sub(r"\s+", " ", enhanced).strip()
    return enhanced, orig_syll, trans_syll_before, trans_syll_after, diff

# ------------------------
# Blending Strategies
# ------------------------

def interleave_words(original, translations_by_lang):
    tokenized = [t.split() for t in translations_by_lang]
    max_len = max(len(t) for t in tokenized) if tokenized else 0
    blended_tokens = []
    for i in range(max_len):
        for tok_list in tokenized:
            if i < len(tok_list):
                blended_tokens.append(tok_list[i])
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
        return " ".join(a_seg + b_seg)
    assembled = []
    for idx, words in enumerate(segments):
        n = len(words)
        start = math.floor(idx * n / len(segments))
        end = math.floor((idx + 1) * n / len(segments))
        if start < end:
            assembled.extend(words[start:end])
        else:
            assembled.extend(words[: max(1, min(3, n))])
    return " ".join(assembled)

def last_word_swap(original, translations_by_lang):
    orig_words = original.strip().split()
    if not orig_words:
        return original
    for t in translations_by_lang:
        tw = t.strip().split()
        if tw:
            new_last = tw[-1]
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

def plot_syllable_comparison(orig_syll, trans_before, trans_after):
    categories = ["Original", "Translated (clean)", "Translated (enhanced)"]
    values = [orig_syll, trans_before, trans_after]
    colors = []
    for v in values:
        diff = abs(v - orig_syll)
        colors.append("#2ecc71" if diff == 0 else "#f1c40f" if diff <= 2 else "#e74c3c")
    fig = go.Figure([go.Bar(x=categories, y=values, marker_color=colors, text=values, textposition="auto")])
    fig.update_layout(title="Syllable Count Comparison", yaxis_title="Syllable count")
    return fig

# ------------------------
# Pronunciation helper
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
        return f"<i>Audio unavailable: {e}</i>"

def simplified_phonetic(text):
    t = text.lower()
    replacements = {
        "á":"a", "é":"e", "í":"i", "ó":"o", "ú":"u",
        "ñ":"ny", "ç":"s", "ü":"u", "ä":"a", "ö":"o",
        "ph":"f", "th":"t", "sh":"sh"
    }
    for k,v in replacements.items():
        t = t.replace(k,v)
    return re.sub(r"[^a-z\s]", "", t)

def ipa_transcription(text):
    ipa = text.lower()
    ipa = ipa.replace("a", "ɑ").replace("e", "ɛ").replace("i", "iː").replace("o", "ɔ").replace("u", "uː")
    ipa = ipa.replace("th", "θ").replace("sh", "ʃ").replace("ch", "tʃ").replace("ph", "f")
    return re.sub(r"[^ɑɛiːɔuːθʃtʃf\s]", "", ipa)

# ------------------------
# Main App
# ------------------------

def main():
    st.set_page_config(page_title="Melosphere — Phase 2 (Polyglot Blending)", layout="wide")
    st.title("🎛️ Melosphere — Phase 2: Polyglot Lyric Blending")

    st.markdown("""
        Generate *multiple translations* of a lyric line and blend them into a multilingual lyric.  
        - Pick 2+ target languages  
        - Choose blending mode  
        - Compare rhythm & pronunciation  
    """)

    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("Enter your lyric line (English):", height=80)
    with col2:
        available_languages = {
            "Spanish": "es", "Kannada": "kn", "Tamil": "ta",
            "Malayalam": "ml", "Hindi": "hi", "Telugu": "te",
            "Japanese": "ja", "French": "fr", "Portuguese": "pt",
            "German": "de", "Korean": "ko"
        }
        selected = st.multiselect("Select target languages:", options=list(available_languages.keys()), default=["Spanish", "Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])
        enhance_rhythm = st.checkbox("✨ Rhythmic Enhancement", value=True)
        fillers_in_blend_only = st.checkbox("Show fillers only in blended output", value=True)
        show_plot = st.checkbox("Show syllable chart", value=False)
        show_dots = st.checkbox("Show syllable dots", value=False)
        show_syllables = st.checkbox("Show syllable counts", value=True)
        show_rhymes = st.checkbox("Show English rhymes", value=True)

    if not lyric_line or not selected:
        st.info("Enter a lyric line and select at least one language.")
        return

    tgt_codes = [available_languages[l] for l in selected]
    translations_clean, translations_enhanced, overall_stats = {}, {}, {}

    for lang_name, code in zip(selected, tgt_codes):
        trans = translate_text(lyric_line, code)
        if enhance_rhythm:
            enhanced, orig_syll, trans_before, trans_after, diff = rhythmic_translation_enhancement(lyric_line, trans)
        else:
            enhanced = trans
            orig_syll = count_syllables_general(lyric_line, "en")
            trans_before = count_syllables_general(trans, code)
            trans_after = trans_before
            diff = orig_syll - trans_before
        if fillers_in_blend_only:
            translations_clean[lang_name] = trans
            translations_enhanced[lang_name] = enhanced
        else:
            translations_clean[lang_name] = enhanced
            translations_enhanced[lang_name] = enhanced
        overall_stats[lang_name] = {"orig_syll": orig_syll, "trans_before": trans_before, "trans_after": trans_after, "diff": diff}

    st.subheader("Translations")
    trans_cols = st.columns(len(selected))
    for col, lang_name in zip(trans_cols, selected):
        with col:
            code = available_languages[lang_name]
            st.markdown(f"**{lang_name} ({code})**")
            st.write(translations_clean[lang_name])
            if show_syllables:
                sc = count_syllables_general(translations_clean[lang_name], available_languages[lang_name])
                st.caption(f"Approx. syllables: {sc}")

    st.subheader("Blended Outputs")
    translations_list_for_blend = [translations_enhanced[name] for name in selected]
    if mode == "Interleave Words":
        blended = interleave_words(lyric_line, translations_list_for_blend)
    elif mode == "Phrase Swap":
        blended = phrase_swap(lyric_line, translations_list_for_blend)
    elif mode == "Last-Word Swap":
        blended = last_word_swap(lyric_line, translations_list_for_blend)
    else:
        blended = lyric_line
    blended = remove_consecutive_duplicates(blended)
    st.markdown("**Blended lyric preview:**")
    st.info(blended)

    if show_syllables:
        st.subheader("Rhythm / Syllable Analysis")
        source_syll = count_syllables_general(lyric_line, "en")
        st.write(f"English syllables ≈ **{source_syll}**")
        for lang_name in selected:
            code = available_languages[lang_name]
            clean_text = translations_clean[lang_name]
            enhanced_text = translations_enhanced[lang_name]
            sc_clean = count_syllables_general(clean_text, code)
            sc_enhanced = count_syllables_general(enhanced_text, code)
            dots_clean = syllable_dots(sc_clean) if show_dots else ""
            dots_enh = syllable_dots(sc_enhanced) if show_dots else ""
            diff_enh = sc_enhanced - source_syll
            if diff_enh == 0:
                status = ("✅ matches", "green")
            elif abs(diff_enh) <= 2:
                status = (f"🟡 near match ({'+' if diff_enh>0 else ''}{diff_enh})", "orange")
            else:
                status = (f"🔴 mismatch ({'+' if diff_enh>0 else ''}{diff_enh})", "red")
            st.markdown(f"**{lang_name}**")
            st.write(f"- Clean syllables: {sc_clean}  {dots_clean}")
            st.write(f"- Enhanced syllables: {sc_enhanced}  {dots_enh}")
            st.markdown(f"- **Status:** <span style='color:{status[1]}'>{status[0]}</span>", unsafe_allow_html=True)

    if show_plot:
        chart_lang = selected[0]
        stats = overall_stats[chart_lang]
        fig = plot_syllable_comparison(stats["orig_syll"], stats["trans_before"], stats["trans_after"])
        st.plotly_chart(fig, use_container_width=True)

    if show_rhymes:
        last_word = lyric_line.strip().split()[-1].lower() if lyric_line.strip().split() else ""
        if last_word:
            rhymes = get_rhymes(last_word)
            if rhymes:
                st.subheader(f"English rhymes for '{last_word}'")
                st.write(", ".join(rhymes))
            else:
                st.subheader("No rhymes found")

    st.subheader("Export")
    st.code(blended, language="text")
    st.download_button("Download blended lyric", blended, file_name="melosphere_blended_lyric.txt")

    # ------------------------
    # Pronunciation Guide Section (IPA default, toggle simplified)
    # ------------------------
    st.subheader("🎙️ Pronunciation Guide")
    show_simple = st.toggle("See simplified style (default = IPA)", value=False)

    for lang_name in selected:
        code = available_languages[lang_name]
        text = translations_clean[lang_name]
        ipa = ipa_transcription(text)
        simp = simplified_phonetic(text)
        st.markdown(f"**{lang_name} pronunciation:**")
        st.markdown(simp if show_simple else ipa)
        st.markdown(generate_tts_audio(text, code), unsafe_allow_html=True)

    st.markdown("""
        **Notes**
        - Syllable counts for non-English are heuristic.
        - Fillers maintain rhythmic flow.
        - Pronunciation shows IPA by default; toggle for simplified.
    """)

if __name__ == "__main__":
    main()
