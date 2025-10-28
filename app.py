import streamlit as st
import requests
import pronouncing
import re
import random

# ========================
# Google Translation API
# ========================

def translate_text(text, target_lang):
    api_key = st.secrets["general"]["GOOGLE_TRANSLATE_API_KEY"]
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {
        "q": text,
        "target": target_lang,
        "format": "text"
    }

    try:
        response = requests.post(url, json=payload)
        data = response.json()
        if "data" in data and "translations" in data["data"]:
            return data["data"]["translations"][0]["translatedText"]
        else:
            return f"Error: {data}"
    except Exception as e:
        return f"Error during translation: {e}"

# ========================
# Rhyming and Syllables
# ========================

def get_rhymes(word):
    response = requests.get(f'https://api.datamuse.com/words?rel_rhy={word}&max=10')
    if response.status_code == 200:
        rhymes = [item['word'] for item in response.json()]
        return rhymes
    else:
        return []

def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    else:
        return sum(1 for char in word.lower() if char in 'aeiou')

def total_syllables_in_line(line):
    words = re.findall(r"\w+", line)
    return sum(count_syllables(w) for w in words)

# ========================
# Rhythmic Translation Enhancement
# ========================

def rhythmic_translation_enhancement(original, translated):
    """
    Enhances rhythm by balancing syllables naturally (no repetition),
    using fillers like 'oh', 'la', 'yeah', etc. if needed.
    Also adds placeholders for stress/beat alignment (future ready).
    """
    fillers = ["oh", "la", "yeah", "na", "ha"]
    orig_syll = total_syllables_in_line(original)
    trans_syll = total_syllables_in_line(translated)
    diff = orig_syll - trans_syll

    if diff > 0:
        # add subtle fillers naturally, not repeated words
        extra = " ".join(random.choices(fillers, k=min(diff, 3)))
        translated = f"{translated} {extra}"

    elif diff < 0:
        # trim overly long translations gracefully
        words = translated.split()
        translated = " ".join(words[:max(1, len(words) + diff)])

    # Placeholder for stress/beat alignment (future version)
    translated = re.sub(r"\s+", " ", translated).strip()

    return translated, orig_syll, trans_syll, diff

# ========================
# Polyglot Blend Function
# ========================

def polyglot_blend(text1, text2, mode="interleave_words", deduplicate=False):
    words1 = text1.split()
    words2 = text2.split()
    result = []

    if mode == "interleave_words":
        for i in range(max(len(words1), len(words2))):
            if i < len(words1):
                result.append(words1[i])
            if i < len(words2):
                result.append(words2[i])

    elif mode == "phrase_swap":
        mid1, mid2 = len(words1)//2, len(words2)//2
        result = words1[:mid1] + words2[mid2:]

    elif mode == "last_word_swap":
        if words1 and words2:
            words1[-1], words2[-1] = words2[-1], words1[-1]
        result = words1 + words2

    blended = " ".join(result)

    if deduplicate:
        seen = []
        final = []
        for w in blended.split():
            if w.lower() not in seen:
                final.append(w)
                seen.append(w.lower())
        blended = " ".join(final)

    return blended

# ========================
# Streamlit App
# ========================

def main():
    st.title("🎵 Melosphere AI - Lyrics Without Limits")

    lyric_line = st.text_input("Enter your Lyric Line (English):")

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

    # Toggles
    col1, col2, col3 = st.columns(3)
    with col1:
        enhance_rhythm = st.toggle("✨ Rhythmic Enhancement", value=True)
    with col2:
        deduplicate = st.toggle("🚫 Deduplicate Blending", value=True)
    with col3:
        blend_mode = st.selectbox("Blending Style:", ["interleave_words", "phrase_swap", "last_word_swap"])

    if lyric_line:
        words = lyric_line.strip().split()
        last_word = words[-1].lower()

        rhymes = get_rhymes(last_word)
        if rhymes:
            st.write(f"**Rhymes for '{last_word}':** {', '.join(rhymes)}")
        else:
            st.write(f"No rhymes found for '{last_word}'.")

        syllables_per_word = {w: count_syllables(w) for w in words}
        total_syllables = sum(syllables_per_word.values())
        st.write(f"**Syllables per word:** {syllables_per_word}")
        st.write(f"**Total syllables:** {total_syllables}")

        translation = translate_text(lyric_line, languages[tgt_lang])

        if enhance_rhythm:
            translation, orig_syll, trans_syll, diff = rhythmic_translation_enhancement(lyric_line, translation)
            st.write(f"🎶 **Rhythmic Enhancement Applied** (Syllable Diff: {diff})")
        else:
            orig_syll = total_syllables_in_line(lyric_line)
            trans_syll = total_syllables_in_line(translation)

        st.write(f"**{tgt_lang} Translation:** {translation}")

        blended = polyglot_blend(lyric_line, translation, blend_mode, deduplicate)
        st.markdown("### 🌐 Polyglot Blend Output:")
        st.write(blended)

        st.markdown("---")
        st.markdown(f"🎵 *Syllables — Original: {orig_syll}, Translated: {trans_syll}*")
        st.markdown("_Future enhancement: Stress pattern modeling & beat-matching to melody lines._")

if __name__ == "__main__":
    main()
