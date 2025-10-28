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
    total = count_syllables_general(text, lang_code)
    pattern = []
    for i in range(total):
        pattern.append(1 if i % 2 == 0 else 0)
    if pattern:
        pattern[-1] = 1
    return pattern

def beat_bar_from_pattern(pattern, max_len=30):
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
    trans_syll_before = count_syllables_general(translated, "xx")
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
    segments = [t.split() for t in translations_by_lang]
    if len(segments) == 1:
        return translations_by_lang[0]
    if len(segments) == 2:
        a, b = segments
        return " ".join(a[:len(a)//2] + b[len(b)//2:])
    assembled = []
    for idx, words in enumerate(segments):
        n = len(words)
        start = math.floor(idx * n / len(segments))
        end = math.floor((idx + 1) * n / len(segments))
        assembled.extend(words[start:end])
    return " ".join(assembled)

def last_word_swap(original, translations_by_lang):
    orig_words = original.strip().split()
    if not orig_words:
        return original
    for t in translations_by_lang:
        tw = t.strip().split()
        if tw:
            return " ".join(orig_words[:-1] + [tw[-1]])
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
# Helper for dot visualization (fix)
# ------------------------

def syllable_dots(count):
    if count <= 0:
        return ""
    dots = "●" * count
    return f"`{dots}`"

# ------------------------
# Streamlit UI
# ------------------------

def main():
    st.set_page_config(page_title="Melosphere — Phase 2 (Polyglot Blending)", layout="wide")
    st.title("🎛️ Melosphere — Phase 2: Polyglot Lyric Blending")

    st.markdown("""
    Generate *multiple* translations of a lyric line and blend them into a multilingual lyric with rhythmic preservation.
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
        selected = st.multiselect("Select target languages:", list(available_languages.keys()), default=["Spanish", "Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])
        enhance_rhythm = st.checkbox("✨ Rhythmic Enhancement", True)
        fillers_in_blend_only = st.checkbox("Show fillers only in blended output", True)
        show_plot = st.checkbox("Show syllable chart", False)
        show_dots = st.checkbox("Show syllable dots", False)
        show_syllables = st.checkbox("Show syllable counts", True)

    if not lyric_line or not selected:
        st.info("Enter a lyric and select languages to start.")
        return

    tgt_codes = [available_languages[l] for l in selected]
    translations_clean, translations_enhanced, stats = {}, {}, {}

    for lang_name, code in zip(selected, tgt_codes):
        clean = translate_text(lyric_line, code)
        if enhance_rhythm:
            enhanced, orig_s, before_s, after_s, diff = rhythmic_translation_enhancement(lyric_line, clean)
        else:
            enhanced = clean
            orig_s = count_syllables_general(lyric_line, "en")
            before_s = after_s = count_syllables_general(clean, code)
            diff = orig_s - before_s
        if fillers_in_blend_only:
            translations_clean[lang_name] = clean
        else:
            translations_clean[lang_name] = enhanced
        translations_enhanced[lang_name] = enhanced
        stats[lang_name] = {"orig": orig_s, "before": before_s, "after": after_s, "diff": diff}

    st.subheader("Translations")
    for lang in selected:
        st.markdown(f"**{lang}:** {translations_clean[lang]}")

    st.subheader("Blended Output")
    enhanced_list = [translations_enhanced[l] for l in selected]
    blended = (interleave_words if mode=="Interleave Words" else phrase_swap if mode=="Phrase Swap" else last_word_swap)(lyric_line, enhanced_list)
    blended = remove_consecutive_duplicates(blended)
    st.success(blended)

    # stress/beat alignment preview
    show_beat_alignment(lyric_line, blended, "xx")

    if show_plot:
        lang = selected[0]
        s = stats[lang]
        fig = go.Figure()
        categories = ["Original", "Translated (clean)", "Translated (enhanced)"]
        values = [s["orig"], s["before"], s["after"]]
        colors = ["#2ecc71", "#f1c40f", "#3498db"]
        fig.add_trace(go.Bar(x=categories, y=values, marker_color=colors, text=values, textposition="auto"))
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
