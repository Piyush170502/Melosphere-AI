import streamlit as st
import requests
import pronouncing
import random
import matplotlib.pyplot as plt

# ========================
# GOOGLE TRANSLATION API
# ========================

def translate_text(text, target_lang):
    """Uses official Google Cloud Translation API with API key from Streamlit secrets."""
    api_key = st.secrets.get("general", {}).get("GOOGLE_TRANSLATE_API_KEY", None)
    if not api_key:
        return "⚠️ Translation API key not found in Streamlit secrets."
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {"q": text, "target": target_lang, "format": "text"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if "data" in data and "translations" in data["data"]:
            return data["data"]["translations"][0]["translatedText"]
        elif "error" in data:
            return f"API error: {data['error'].get('message','unknown')}"
    except Exception as e:
        return f"Error during translation: {e}"

# ========================
# RHYME AND SYLLABLE HELPERS
# ========================

def get_rhymes(word):
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        return [item['word'] for item in response.json()]
    return []

def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for c in word.lower() if c in 'aeiou')

def count_total_syllables(line):
    words = line.split()
    return sum(count_syllables(w) for w in words)

# ========================
# RHYTHMIC TRANSLATION ENHANCEMENTS
# ========================

def rhythmically_align(source_line, translated_line):
    """Adjusts translation rhythm using neutral fillers instead of repeating words."""
    source_syll = count_total_syllables(source_line)
    target_syll = count_total_syllables(translated_line)

    diff = source_syll - target_syll
    if diff <= 0:
        return translated_line, target_syll, target_syll  # already matches or longer

    fillers = ["oh", "yeah", "baby", "la", "na", "hey", "mmm"]
    add_fillers = " ".join(random.choices(fillers, k=min(diff, 3)))  # add up to 3 fillers
    enhanced_line = f"{translated_line}, {add_fillers}"
    enhanced_syll = count_total_syllables(enhanced_line)
    return enhanced_line, target_syll, enhanced_syll

# ========================
# POLYGLOT BLENDING
# ========================

def polyglot_blend(lines, deduplicate=True, mode="interleave"):
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]

    blended = []
    words1, words2 = lines[0].split(), lines[1].split()
    len1, len2 = len(words1), len(words2)

    if mode == "interleave":
        for i in range(max(len1, len2)):
            if i < len1:
                blended.append(words1[i])
            if i < len2:
                blended.append(words2[i])
    elif mode == "phrase_swap":
        half1, half2 = len1 // 2, len2 // 2
        blended = words1[:half1] + words2[half2:] + words2[:half2] + words1[half1:]
    elif mode == "last_word_swap":
        if words1 and words2:
            words1[-1], words2[-1] = words2[-1], words1[-1]
        blended = words1 + words2
    else:
        blended = words1 + words2

    if deduplicate:
        seen = set()
        dedup = []
        for w in blended:
            lw = w.lower()
            if lw not in seen:
                seen.add(lw)
                dedup.append(w)
        blended = dedup

    return " ".join(blended)

# ========================
# BEAT ALIGNMENT VISUALIZATION
# ========================

def show_rhythm_chart(source_syll, target_syll, enhanced_syll):
    """Displays a simple syllable count bar comparison."""
    categories = ["English (Source)", "Translated", "Enhanced"]
    counts = [source_syll, target_syll, enhanced_syll]
    colors = ["#3498db", "#e67e22", "#2ecc71"]

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(categories, counts, color=colors)
    ax.set_title("🎵 Syllable Rhythm Alignment")
    ax.set_ylabel("Syllable Count")
    for i, v in enumerate(counts):
        ax.text(i, v + 0.1, str(v), ha='center', fontweight='bold')
    st.pyplot(fig)

# ========================
# STREAMLIT APP
# ========================

def main():
    st.title("🎵 Melosphere AI – Lyrics Without Limits (Phase 2 Enhanced)")

    lyric_line = st.text_input("Enter your lyric line (English):")
    languages = {
        "Spanish": "es",
        "Kannada": "kn",
        "Tamil": "ta",
        "Malayalam": "ml",
        "Hindi": "hi",
        "Telugu": "te",
        "Japanese": "ja",
    }

    tgt_lang = st.selectbox("Select target language for translation:", list(languages.keys()))
    mode = st.radio("Polyglot blend mode:", ["interleave", "phrase_swap", "last_word_swap"])
    dedup = st.toggle("🧹 Remove duplicates in blending", value=True)
    rhythm_enhance = st.toggle("🎵 Enable rhythmic translation enhancement", value=True)
    show_preview = st.toggle("👁️ Preview Beat Alignment Chart", value=True)

    if lyric_line:
        st.subheader("✨ Rhymes and Syllables")
        words = lyric_line.strip().split()
        last_word = words[-1].lower()
        rhymes = get_rhymes(last_word)
        st.write(f"**Rhymes for '{last_word}':** {', '.join(rhymes) if rhymes else 'None found.'}")

        syllables_per_word = {w: count_syllables(w) for w in words}
        total_syllables = sum(syllables_per_word.values())
        st.write(f"**Syllables per word:** {syllables_per_word}")
        st.write(f"**Total syllables:** {total_syllables}")

        # Translation and enhancement
        translation = translate_text(lyric_line, languages[tgt_lang])
        if rhythm_enhance and not translation.startswith("Error"):
            enhanced_line, target_syll, enhanced_syll = rhythmically_align(lyric_line, translation)
        else:
            enhanced_line, target_syll, enhanced_syll = translation, count_total_syllables(translation), count_total_syllables(translation)

        st.subheader("🌍 Translation Output")
        st.write(f"**{tgt_lang} Translation:** {translation}")
        if rhythm_enhance:
            st.write(f"**Enhanced Translation:** {enhanced_line}")

        if show_preview:
            show_rhythm_chart(total_syllables, target_syll, enhanced_syll)

        # Polyglot blending
        poly_lines = [lyric_line, enhanced_line if rhythm_enhance else translation]
        st.subheader("🌐 Polyglot Blend")
        blended = polyglot_blend(poly_lines, deduplicate=dedup, mode=mode)
        st.write(blended)

        st.caption("🧠 Rhythmic model preserves syllable flow using fillers like 'oh', 'yeah', 'na' etc. "
                   "Future updates will integrate stress pattern modeling and beat-matching with melody lines.")

if __name__ == "__main__":
    main()
