import streamlit as st
import requests
import pronouncing
import math
import random
import re
import plotly.graph_objects as go

# ------------------------
# Helper: Translation
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
# Stress / Beat Alignment (New Logic)
# ------------------------

def approximate_stress_pattern(text, lang_code):
    """
    Approximate a stress pattern for a line:
    Returns a list of 0/1 per syllable: 1 = stressed, 0 = unstressed.
    Very rough heuristic: alternate stress, emphasise last syllable.
    """
    total = count_syllables_general(text, lang_code)
    pattern = []
    for i in range(total):
        if i % 2 == 0:
            pattern.append(1)  # stress on even
        else:
            pattern.append(0)
    # ensure last syllable is stressed
    if pattern:
        pattern[-1] = 1
    return pattern

def beat_bar_from_pattern(pattern, max_len=30):
    # Map 1 → “●”, 0 → “○”
    bar = "".join("●" if p == 1 else "○" for p in pattern[:max_len])
    if len(pattern) > max_len:
        bar += "...(+%d)" % (len(pattern) - max_len)
    return bar

def show_beat_alignment(original, translated, lang_code):
    pat_orig = approximate_stress_pattern(original, "en")
    pat_trans = approximate_stress_pattern(translated, lang_code)
    st.markdown("**Stress / Beat Alignment Preview:**")
    st.text(f"English (source): {beat_bar_from_pattern(pat_orig)}")
    st.text(f"Translated      : {beat_bar_from_pattern(pat_trans)}")
    # Optionally, calculate a simple score
    match_count = sum(1 for i, p in enumerate(pat_trans[:len(pat_orig)]) if i < len(pat_orig) and p == pat_orig[i])
    score = match_count / max(len(pat_orig),1)
    st.caption(f"Alignment score: {score:.2f} (1.0 = perfect)")

# ------------------------
# Smart filler insertion (non-random placement)
# ------------------------

def _build_fillers(diff, max_fillers=3):
    fillers_mild = ["oh", "la", "na", "hey"]
    fillers_strong = ["yeah", "baby", "mmm", "uh"]
    if diff <= 2:
        pool = fillers_mild
    else:
        pool = fillers_mild + fillers_strong
    k = min(max_fillers, max(0, diff))
    chosen = random.sample(pool, k) if k <= len(pool) else [random.choice(pool) for _ in range(k)]
    return " ".join(chosen)

def insert_fillers_safely(translated_text, fillers_str):
    if not fillers_str:
        return translated_text
    t = translated_text.strip()
    # punctuation boundary
    m = re.search(r'([.!?])\s*$', t)
    if m:
        base = t[:m.start()].rstrip()
        punct = m.group(1)
        return f"{base}, {fillers_str}{punct}"
    last_comma = t.rfind(',')
    if last_comma != -1 and last_comma < len(t) - 1:
        return f"{t[:last_comma+1]} {fillers_str}{t[last_comma+1:]}"
    words = t.split()
    if len(words) >= 2:
        return " ".join(words[:-1] + [fillers_str, words[-1]])
    return f"{t}, {fillers_str}"

def rhythmic_translation_enhancement(original, translated, max_fillers=3):
    orig_syll = count_syllables_general(original, "en")
    trans_syll_before = count_syllables_general(translated, "xx")  # generic lang
    diff = orig_syll - trans_syll_before
    if diff <= 0:
        enhanced = translated.strip()
        trans_syll_after = trans_syll_before
    else:
        fillers_str = _build_fillers(diff, max_fillers=max_fillers)
        enhanced = insert_fillers_safely(translated, fillers_str)
        trans_syll_after = count_syllables_general(enhanced, "xx")
    enhanced = re.sub(r"\s+", " ", enhanced).strip()
    return enhanced, orig_syll, trans_syll_before, trans_syll_after, diff

# ------------------------
# Blending Strategies (unchanged)
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

def remove_consecutive_duplicates(text):
    words = text.split()
    if not words:
        return ""
    out = [words[0]]
    for w in words[1:]:
        if w != out[-1]:
            out.append(w)
    return " ".join(out)

# ------------------------
# Streamlit UI (unchanged layout) + toggles for new logic
# ------------------------

def main():
    st.set_page_config(page_title="Melosphere — Phase 2 (Polyglot Blending)", layout="wide")
    st.title("🎛️ Melosphere — Phase 2: Polyglot Lyric Blending")

    st.markdown("""
    This screen lets you generate *multiple* translations of a lyric line and blend them into a single multilingual lyric.
    - Pick 2 or more target languages.
    - Choose a blending mode and inspect syllable counts to preserve rhythm.
    """)

    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("Enter your lyric line (source language = English):", height=80)
    with col2:
        available_languages = {
            "Spanish": "es", "Kannada": "kn", "Tamil": "ta",
            "Malayalam": "ml", "Hindi": "hi", "Telugu": "te",
            "Japanese": "ja", "French": "fr", "Portuguese": "pt",
            "German": "de", "Korean": "ko"
        }
        selected = st.multiselect("Select 2+ target languages (for blending):",
                                  options=list(available_languages.keys()),
                                  default=["Spanish", "Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])
        enhance_rhythm = st.checkbox("✨ Rhythmic Enhancement", value=True)
        fillers_in_blend_only = st.checkbox("Show fillers only in blended output (keep translation clean)", value=True)
        show_plot = st.checkbox("Show syllable comparison chart (Plotly)", value=False)
        show_dots = st.checkbox("Show syllable dots visual", value=False)
        show_syllables = st.checkbox("Show syllable hints / rhythm warnings", value=True)
        show_rhymes = st.checkbox("Show English rhymes for the last word (only English)", value=True)

    if not lyric_line or not selected:
        st.info("Enter a lyric line and select at least one language to see translations and blends.")
        return

    tgt_codes = [available_languages[l] for l in selected]
    translations_clean = {}
    translations_enhanced = {}
    stats = {}

    for lang_name, code in zip(selected, tgt_codes):
        clean = translate_text(lyric_line, code)
        if enhance_rhythm:
            enhanced, orig_s, before_s, after_s, diff = rhythmic_translation_enhancement(lyric_line, clean)
        else:
            enhanced = clean
            orig_s = count_syllables_general(lyric_line, "en")
            before_s = count_syllables_general(clean, code)
            after_s = before_s
            diff = orig_s - before_s

        if fillers_in_blend_only:
            translations_clean[lang_name] = clean
            translations_enhanced[lang_name] = enhanced
        else:
            translations_clean[lang_name] = enhanced
            translations_enhanced[lang_name] = enhanced

        stats[lang_name] = {"orig": orig_s, "before": before_s, "after": after_s, "diff": diff}

    # Display translations (clean)
    st.subheader("Translations")
    cols = st.columns(len(selected))
    for c, lang_name in zip(cols, selected):
        with c:
            code = available_languages[lang_name]
            st.markdown(f"**{lang_name} ({code})**")
            st.write(translations_clean[lang_name])
            if show_syllables:
                sc = count_syllables_general(translations_clean[lang_name], available_languages[lang_name])
                st.caption(f"Approx. syllables: {sc}")

    # Blended Outputs
    st.subheader("Blended Outputs")
    enhanced_list = [translations_enhanced[name] for name in selected]
    if mode == "Interleave Words":
        blended = interleave_words(lyric_line, enhanced_list)
    elif mode == "Phrase Swap":
        blended = phrase_swap(lyric_line, enhanced_list)
    elif mode == "Last-Word Swap":
        blended = last_word_swap(lyric_line, enhanced_list)
    else:
        blended = lyric_line

    blended = remove_consecutive_duplicates(blended)
    st.markdown("**Blended lyric preview:**")
    st.info(blended)

    # Syllable analysis & warnings
    if show_syllables:
        st.subheader("Rhythm / Syllable Analysis")
        source_syll = count_syllables_general(lyric_line, "en")
        st.write(f"Source (English) total syllables ≈ **{source_syll}**")

        for lang_name in selected:
            code = available_languages[lang_name]
            clean_txt = translations_clean[lang_name]
            enh_txt = translations_enhanced[lang_name]
            sc_clean = count_syllables_general(clean_txt, code)
            sc_enh = count_syllables_general(enh_txt, code)
            dots_clean = syllable_dots(sc_clean) if show_dots else ""
            dots_enh = syllable_dots(sc_enh) if show_dots else ""
            diff = sc_enh - source_syll
            if diff == 0:
                status = ("✅ matches source", "green")
            elif abs(diff) <= 2:
                status = (f"🟡 near match ({'+' if diff>0 else ''}{diff})", "orange")
            else:
                status = (f"🔴 mismatch ({'+' if diff>0 else ''}{diff})", "red")

            st.markdown(f"**{lang_name}**")
            st.write(f"- Clean translation syllables: {sc_clean}  {dots_clean}")
            st.write(f"- Enhanced translation syllables: {sc_enh}  {dots_enh}")
            st.markdown(f"- **Status:** <span style='color:{status[1]}'>{status[0]}</span>", unsafe_allow_html=True)

    # Plotly chart if requested
    if show_plot:
        chart_lang = selected[0]
        s = stats[chart_lang]
        fig = go.Figure()
        categories = ["Original", "Translated (clean)", "Translated (enhanced)"]
        values = [s["orig"], s["before"], s["after"]]
        colors = ["#2ecc71" if v==s["orig"] else "#f1c40f" if abs(v-s["orig"])<=2 else "#e74c3c"
                  for v in values]
        fig.add_trace(go.Bar(x=categories, y=values, marker_color=colors, text=values, textposition="auto"))
        fig.update_layout(title=f"Syllable Count Comparison — {chart_lang}", yaxis_title="Syllable count")
        st.plotly_chart(fig, use_container_width=True)

    # Rhymes
    if show_rhymes:
        last_word = lyric_line.strip().split()[-1].lower() if lyric_line.strip().split() else ""
        if last_word:
            rhymes = get_rhymes(last_word)
            if rhymes:
                st.subheader(f"English rhymes for '{last_word}'")
                st.write(", ".join(rhymes))
            else:
                st.subheader("No English rhymes found")

    # Export
    st.subheader("Export")
    st.write("You can copy the blended lyric below.")
    st.code(blended, language="text")
    st.download_button("Download blended lyric as .txt", blended, file_name="melosphere_blended_lyric.txt")

    st.markdown("""
    **Notes & limitations**
    - Syllable counts for non-English languages are heuristic and approximate.
    - Rhythmic enhancement now uses natural fillers placed musically (not just numeric).
    - Stress / beat alignment modeling is built in as a preview — full prosody modelling to come in future versions.
    """)

if __name__ == "__main__":
    main()
