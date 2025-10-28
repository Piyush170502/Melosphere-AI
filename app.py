import streamlit as st
import requests
import pronouncing
import math

# ------------------------
# Google Translation Helper
# ------------------------

def translate_text(text, target_lang):
    api_key = st.secrets.get("general", {}).get("GOOGLE_TRANSLATE_API_KEY", None)
    if not api_key:
        return "⚠️ Translation API key missing in Streamlit secrets."
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {"q": text, "target": target_lang, "format": "text"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if "data" in data and "translations" in data["data"]:
            return data["data"]["translations"][0]["translatedText"]
        elif "error" in data:
            return f"API error: {data['error'].get('message','unknown')}"
    except Exception as e:
        return f"Error during translation: {e}"

# ------------------------
# Syllable / Stress utilities
# ------------------------

def count_syllables_english(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for ch in word.lower() if ch in "aeiou")

def count_syllables_heuristic(text):
    text = str(text)
    for ch in ",.!?;:-—()\"'":
        text = text.replace(ch, " ")
    words = [w for w in text.split() if w.strip()]
    total = 0
    for w in words:
        lw = w.lower()
        prev_v = False
        groups = 0
        for ch in lw:
            is_v = ch in "aeiouáàâäãåāéèêëēíìîïīóòôöõōúùûüūy"
            if is_v and not prev_v:
                groups += 1
            prev_v = is_v
        total += groups if groups else 1
    return total

def count_syllables_general(text, lang_code):
    if not text or not isinstance(text, str):
        return 0
    if lang_code.startswith("en"):
        return sum(count_syllables_english(w) for w in text.split())
    return count_syllables_heuristic(text)

def approximate_stress_pattern(text, lang_code):
    """
    Roughly mark stressed syllables by alternating pattern (1=stress,0=unstress).
    """
    syll = count_syllables_general(text, lang_code)
    pattern = [(i % 2) for i in range(syll)]
    return pattern

def beat_bar(pattern):
    """Return a simple visual beat bar from stress pattern."""
    bar = "".join("●" if p else "○" for p in pattern)
    return bar if bar else "○"

# ------------------------
# Rhythm adjustment
# ------------------------

def adjust_translation_rhythm(orig, trans, lang_code):
    o_syll = count_syllables_general(orig, "en")
    t_syll = count_syllables_general(trans, lang_code)
    diff = t_syll - o_syll
    words = trans.split()

    if abs(diff) <= 1:
        return trans
    elif diff > 1:
        # remove extra filler words to shorten
        return " ".join(words[:-abs(diff)]) if len(words) > abs(diff) else trans
    else:
        # too short: repeat last stressed word
        last = words[-1] if words else ""
        return trans + " " + " ".join([last] * abs(diff))

# ------------------------
# Blending Strategies
# ------------------------

def interleave_words(original, translations_by_lang):
    tokenized = [t.split() for t in translations_by_lang]
    max_len = max(len(t) for t in tokenized) if tokenized else 0
    blended = []
    for i in range(max_len):
        for toks in tokenized:
            if i < len(toks):
                blended.append(toks[i])
    return " ".join(blended)

def phrase_swap(original, translations_by_lang):
    segs = [t.split() for t in translations_by_lang]
    if len(segs) == 1:
        return translations_by_lang[0]
    if len(segs) == 2:
        a, b = segs
        return " ".join(a[: math.ceil(len(a)/2)] + b[math.floor(len(b)/2):])
    blended = []
    for idx, words in enumerate(segs):
        n = len(words)
        start = math.floor(idx * n / len(segs))
        end = math.floor((idx + 1) * n / len(segs))
        blended.extend(words[start:end] if start < end else words[:2])
    return " ".join(blended)

def last_word_swap(original, translations_by_lang):
    ow = original.strip().split()
    if not ow:
        return original
    for t in translations_by_lang:
        tw = t.strip().split()
        if tw:
            return " ".join(ow[:-1] + [tw[-1]])
    return original

# ------------------------
# Rhymes helper
# ------------------------

def get_rhymes(word):
    try:
        r = requests.get(f"https://api.datamuse.com/words?rel_rhy={word}&max=10", timeout=6)
        if r.status_code == 200:
            return [w["word"] for w in r.json()]
    except Exception:
        pass
    return []

# ------------------------
# Streamlit UI
# ------------------------

def main():
    st.set_page_config(page_title="Melosphere — Polyglot + Rhythm", layout="wide")
    st.title("🎛️ Melosphere — Phase 2 & 2.5 : Polyglot Blending + Rhythmic Enhancement")

    st.markdown(
        "Compose multilingual lyrics that preserve rhythm and musicality across languages."
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("🎵 Enter your lyric line (English):", height=80)
    with col2:
        langs = {
            "Spanish": "es", "Kannada": "kn", "Tamil": "ta", "Malayalam": "ml",
            "Hindi": "hi", "Telugu": "te", "Japanese": "ja", "French": "fr",
            "Portuguese": "pt", "German": "de", "Korean": "ko"
        }
        selected = st.multiselect("Select 2+ target languages:", list(langs.keys()), default=["Spanish","Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words","Phrase Swap","Last-Word Swap"])
        dedup = st.checkbox("Remove duplicates", value=False)
        show_syll = st.checkbox("Show rhythm & syllable analysis", value=True)
        rhythm_enhance = st.checkbox("Enable rhythmic enhancement", value=True)
        show_rhymes = st.checkbox("Show English rhymes", value=True)

    if not lyric_line or not selected:
        st.info("Enter a lyric and select at least one language.")
        return

    # Translations
    st.subheader("Translations")
    translations = {}
    for name in selected:
        code = langs[name]
        t = translate_text(lyric_line, code)
        if rhythm_enhance:
            t = adjust_translation_rhythm(lyric_line, t, code)
        translations[name] = t

    cols = st.columns(len(selected))
    for c, name in zip(cols, selected):
        with c:
            code = langs[name]
            st.markdown(f"**{name} ({code})**")
            st.write(translations[name])
            if show_syll:
                sc = count_syllables_general(translations[name], code)
                st.caption(f"Syllables ≈ {sc}")

    # Blending
    st.subheader("Blended Output")
    trans_list = [translations[n] for n in selected]
    blended = (
        interleave_words(lyric_line, trans_list)
        if mode == "Interleave Words"
        else phrase_swap(lyric_line, trans_list)
        if mode == "Phrase Swap"
        else last_word_swap(lyric_line, trans_list)
    )

    if dedup:
        seen, final = set(), []
        for w in blended.split():
            if w.lower() not in seen:
                final.append(w)
                seen.add(w.lower())
        blended = " ".join(final)

    st.info(blended)

    # Rhythm visualization
    if show_syll:
        st.subheader("🎼 Rhythm Visualizer")
        o_pat = approximate_stress_pattern(lyric_line, "en")
        st.caption(f"Original ({len(o_pat)} syllables) {beat_bar(o_pat)}")
        for name in selected:
            code = langs[name]
            pat = approximate_stress_pattern(translations[name], code)
            st.caption(f"{name} ({len(pat)} syllables) {beat_bar(pat)}")

    # Rhymes
    if show_rhymes:
        last = lyric_line.strip().split()[-1].lower() if lyric_line.strip() else ""
        rhymes = get_rhymes(last)
        st.subheader(f"Rhymes for '{last}'")
        st.write(", ".join(rhymes) if rhymes else "No rhymes found.")

    # Export
    st.subheader("Export")
    st.code(blended, language="text")
    st.download_button("Download blended lyric", blended, file_name="melosphere_polyglot_rhythm.txt")

    st.markdown(
        """
        **Notes**
        - Rhythmic enhancement balances syllable counts automatically.
        - Beat-bar shows stressed(●) vs unstressed(○) syllables for rough alignment.
        - Stress and beat patterns are heuristic — tune manually for melody precision.
        """
    )


if __name__ == "__main__":
    main()
