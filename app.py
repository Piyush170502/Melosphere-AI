import streamlit as st
from googletrans import Translator
from google.cloud import translate_v2 as translate
import pronouncing
import requests
import re
import plotly.graph_objects as go

# -----------------------
# Google Translate setup
# -----------------------
def google_translate_text(text, target_language):
    try:
        client = translate.Client()
        result = client.translate(text, target_language=target_language)
        return result["translatedText"]
    except Exception as e:
        return f"Error during translation: {e}"

# -----------------------
# Syllable counting helper
# -----------------------
def count_syllables(text):
    words = re.findall(r"\w+", text)
    count = 0
    for w in words:
        phones = pronouncing.phones_for_word(w.lower())
        if phones:
            count += pronouncing.syllable_count(phones[0])
        else:
            vowels = len(re.findall(r"[aeiouAEIOU]", w))
            count += max(1, vowels)
    return count

# -----------------------
# Rhythmic Enhancement
# -----------------------
def rhythmic_enhancement(original, translated):
    orig_syll = count_syllables(original)
    trans_syll = count_syllables(translated)
    diff = orig_syll - trans_syll

    if diff > 0:
        translated += " " + "la " * min(diff, 3)
    elif diff < 0:
        translated = " ".join(translated.split()[:diff])

    return translated.strip(), orig_syll, trans_syll

# -----------------------
# Polyglot blending
# -----------------------
def polyglot_blend(text1, text2, mode="interleave_words", deduplicate=False):
    words1 = text1.split()
    words2 = text2.split()
    result = []

    if mode == "interleave_words":
        for w1, w2 in zip(words1, words2):
            result.append(w1)
            result.append(w2)
        result.extend(words1[len(words2):] + words2[len(words1):])

    elif mode == "phrase_swap":
        mid1 = len(words1)//2
        mid2 = len(words2)//2
        result = words1[:mid1] + words2[mid2:]

    elif mode == "last_word_swap":
        if words1 and words2:
            words1[-1], words2[-1] = words2[-1], words1[-1]
        result = words1 + words2

    blended = " ".join(result)

    if deduplicate:
        deduped_words = []
        for w in blended.split():
            if not deduped_words or deduped_words[-1].lower() != w.lower():
                deduped_words.append(w)
        blended = " ".join(deduped_words)

    return blended

# -----------------------
# Streamlit UI
# -----------------------
st.title("🎶 Melosphere AI — Polyglot Lyrics Studio")
st.markdown("Create multilingual, rhythmic, and natural blended lyrics 🌏🎵")

text = st.text_area("Enter your base lyrics (e.g. English line):", height=120)
target_lang = st.text_input("Target language (e.g. ta, hi, ml, ja, etc.):", "ta")

col1, col2, col3 = st.columns(3)
with col1:
    enhance_rhythm = st.toggle("✨ Rhythmic Enhancement", value=True)
with col2:
    show_chart = st.toggle("📊 Show Rhythm Analysis", value=False)
with col3:
    deduplicate = st.toggle("🚫 Deduplicate Blending", value=True)

blend_mode = st.radio("Choose blending style:", ["interleave_words", "phrase_swap", "last_word_swap"])

if st.button("Translate & Blend"):
    if not text.strip():
        st.warning("Please enter some lyrics to translate!")
    else:
        with st.spinner("Translating..."):
            translator = Translator()
            translated_text = translator.translate(text, dest=target_lang).text
            if enhance_rhythm:
                translated_text, orig_syll, trans_syll = rhythmic_enhancement(text, translated_text)
            else:
                orig_syll = count_syllables(text)
                trans_syll = count_syllables(translated_text)

        st.subheader("🎵 Translated Lyrics:")
        st.text_area("Output", translated_text, height=120)

        blended_output = polyglot_blend(text, translated_text, blend_mode, deduplicate)
        st.subheader("🌐 Polyglot Blended Lyrics:")
        st.text_area("Blended Output", blended_output, height=140)

        # Rhythm chart toggle
        if show_chart:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["Original", "Translated"],
                y=[orig_syll, trans_syll],
                text=[orig_syll, trans_syll],
                textposition="auto",
                marker_color=["#636EFA", "#EF553B"]
            ))
            fig.update_layout(
                title="Syllable Count Comparison (Rhythmic Balance)",
                xaxis_title="Line Type",
                yaxis_title="Syllables",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("💡 *Future enhancements:* stress pattern modeling & beat-matching with melody lines for precise musical alignment.")
