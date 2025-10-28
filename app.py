import streamlit as st
import requests
import pronouncing
import plotly.graph_objects as go
from googletrans import Translator
from gtts import gTTS
import eng_to_ipa as ipa
import os
import re
import tempfile
import pandas as pd

translator = Translator()

# ---------------------- Utility Functions ----------------------

def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return max(1, len(re.findall(r'[aeiouy]+', word.lower())))

def syllable_dots(text):
    return " • ".join([f"{w}({count_syllables(w)})" for w in text.split()])

def translate_text(text, target_lang):
    try:
        return translator.translate(text, dest=target_lang).text
    except Exception as e:
        return f"[Translation failed: {e}]"

def simplify_phonetic(text):
    replacements = {
        "ph": "f", "ght": "t", "tion": "shun", "ough": "aw", "ch": "ch",
        "ee": "ee", "ea": "ee", "ie": "ai", "ei": "ai", "oo": "oo"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def add_fillers(translated_text, reference_syllables):
    words = translated_text.split()
    total_syllables = sum(count_syllables(w) for w in words)
    diff = reference_syllables - total_syllables
    fillers = ["la", "na", "ta", "ra", "ha"]
    if diff > 0:
        # Add fillers where natural pauses occur (after verbs/nouns)
        for i in range(diff):
            insert_pos = (i * 2) % (len(words) + 1)
            words.insert(insert_pos, fillers[i % len(fillers)])
    elif diff < 0:
        # Trim softly if overshoot
        words = words[:diff]
    return " ".join(words)

def generate_audio(text, lang_code, filename):
    try:
        tts = gTTS(text=text, lang=lang_code)
        tts.save(filename)
        return True
    except Exception:
        return False

# ---------------------- Stress/Beat Alignment (Simplified Placeholder) ----------------------

def stress_align(text):
    # Placeholder for real prosody/stress alignment — currently a balanced syllabic emphasis
    words = text.split()
    aligned = []
    for i, w in enumerate(words):
        if i % 2 == 0:
            aligned.append(w.upper())
        else:
            aligned.append(w.lower())
    return " ".join(aligned)

# ---------------------- Streamlit UI ----------------------

def main():
    st.set_page_config(page_title="Melosphere AI - Polyglot Lyric Enhancer", layout="wide")
    st.title("🎵 Melosphere AI - Polyglot Lyric Enhancer")

    st.markdown("### Enter your lyrics")
    lyrics = st.text_area("Write or paste your lyrics here:", height=150)

    st.markdown("### Select languages for translation and blending")
    langs = {
        "Tamil": "ta", "Japanese": "ja", "Spanish": "es",
        "Hindi": "hi", "French": "fr", "Korean": "ko"
    }
    selected_langs = st.multiselect("Choose target languages:", list(langs.keys()))

    show_chart = st.toggle("📊 Show Syllable Comparison Chart")
    show_dots = st.toggle("⚪ Show Syllable Dot Comparison")
    show_pronounce = st.toggle("🗣 Show Pronunciation Guide")
    show_audio = st.toggle("🎧 Enable Audio Playback")

    if lyrics and selected_langs:
        st.subheader("🌐 Translations and Enhancements")

        # Base syllable count for comparison
        ref_syllables = sum(count_syllables(w) for w in lyrics.split())

        all_results = {}
        chart_data = []

        for lang in selected_langs:
            code = langs[lang]
            translated = translate_text(lyrics, code)
            enhanced = add_fillers(translated, ref_syllables)
            enhanced = stress_align(enhanced)

            sc_clean = sum(count_syllables(w) for w in translated.split())
            sc_enhanced = sum(count_syllables(w) for w in enhanced.split())

            all_results[lang] = {
                "translated": translated,
                "enhanced": enhanced,
                "sc_clean": sc_clean,
                "sc_enhanced": sc_enhanced
            }

            chart_data.append({
                "Language": lang,
                "Type": "Translated",
                "Syllables": sc_clean
            })
            chart_data.append({
                "Language": lang,
                "Type": "Enhanced",
                "Syllables": sc_enhanced
            })

        # ---------------- Chart Section ----------------
        if show_chart:
            st.markdown("### 📊 Syllable Comparison Chart")
            df = pd.DataFrame(chart_data)
            fig = go.Figure()
            for lang in selected_langs:
                lang_df = df[df["Language"] == lang]
                fig.add_trace(go.Bar(
                    x=lang_df["Type"], y=lang_df["Syllables"], name=lang
                ))
            fig.update_layout(barmode='group', title="Syllable Comparison Across Languages")
            st.plotly_chart(fig, use_container_width=True)

        # ---------------- Result Display ----------------
        for lang in selected_langs:
            res = all_results[lang]
            st.markdown(f"### 🎶 {lang}")

            st.markdown("**Translated:**")
            st.write(res["translated"])

            st.markdown("**Enhanced (Blended):**")
            st.write(res["enhanced"])

            if show_dots:
                dots_clean = syllable_dots(res["translated"])
                dots_enhanced = syllable_dots(res["enhanced"])
                st.markdown("**Syllable Analysis:**")
                st.write(f"Translated: {dots_clean}")
                st.write(f"Enhanced: {dots_enhanced}")

            # ---------------- Pronunciation Guide ----------------
            if show_pronounce:
                st.markdown("**🗣 Pronunciation Guide:**")
                ipa_view = ipa.convert(res["translated"])
                simplified = simplify_phonetic(res["translated"])
                toggle_style = st.toggle(f"Switch to Simplified ({lang})", key=f"simple_{lang}")
                st.write(simplified if toggle_style else ipa_view)

            # ---------------- Audio Playback ----------------
            if show_audio:
                play_enhanced = st.toggle(f"Play Enhanced Version ({lang})", key=f"play_enh_{lang}")
                filename = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                text_to_play = res["enhanced"] if play_enhanced else res["translated"]
                if generate_audio(text_to_play, langs[lang], filename):
                    st.audio(filename)
                else:
                    st.warning("Audio generation failed.")

if __name__ == "__main__":
    main()
