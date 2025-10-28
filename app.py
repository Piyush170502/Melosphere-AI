import streamlit as st
import requests
from google.cloud import translate_v2 as translate
import pronouncing
import re
import plotly.graph_objects as go

# Initialize Google Translator
translator = translate.Client()

# --- Utility functions ---
def syllable_count(text):
    words = re.findall(r'\b\w+\b', text)
    total = 0
    for w in words:
        phones = pronouncing.phones_for_word(w.lower())
        if phones:
            total += pronouncing.syllable_count(phones[0])
        else:
            total += max(1, len(re.findall(r'[aeiouy]+', w.lower())))
    return total

def add_fillers_to_match(source_line, target_line):
    source_syll = syllable_count(source_line)
    target_syll = syllable_count(target_line)
    diff = source_syll - target_syll

    if diff <= 0:
        return target_line, 0

    fillers = ["yeah", "oh", "na", "la", "ha"]
    words = target_line.split()

    # insert fillers at natural pauses like after commas or end of short phrases
    insert_positions = [i for i, w in enumerate(words) if re.search(r'[,.!?]$', w)]
    while diff > 0:
        if insert_positions:
            pos = insert_positions.pop(0)
        else:
            pos = min(len(words), max(1, len(words)//2))
        f = fillers[diff % len(fillers)]
        words.insert(pos, f)
        diff -= syllable_count(f)
    return " ".join(words), source_syll - target_syll

def visualize_syllable_dots(syll_count, max_len=20):
    dots = "⚫" * min(syll_count, max_len)
    return dots

def plot_syllable_difference_chart(lines, syllable_data):
    fig = go.Figure()
    for lang, counts in syllable_data.items():
        fig.add_trace(go.Bar(
            x=list(range(len(lines))),
            y=counts,
            name=lang
        ))
    fig.update_layout(
        title="Syllable Count Comparison",
        xaxis_title="Line Index",
        yaxis_title="Syllable Count",
        barmode='group',
        template='plotly_white'
    )
    return fig

# --- Streamlit UI (UNCHANGED LAYOUT) ---
st.title("🎵 Melosphere: Polyglot Lyric Blender")

source_text = st.text_area("Enter English lyrics:")
languages = st.multiselect("Select languages for translation:", ["ta", "ml", "hi", "ja", "es", "fr"], default=["ta", "ml"])
show_filler_toggle = st.checkbox("Enable Rhythmic Enhancement (Natural Fillers)")
show_chart_toggle = st.checkbox("Show Rhythm Chart (Plotly)")
show_dot_toggle = st.checkbox("Show Syllable Dots")

if st.button("Generate Translations & Blend"):
    if not source_text.strip():
        st.warning("Please enter lyrics.")
    else:
        st.subheader("🌐 Translations")
        translated_lines = {}
        lines = [line.strip() for line in source_text.split("\n") if line.strip()]

        for lang in languages:
            translated_lines[lang] = []
            for line in lines:
                try:
                    result = translator.translate(line, target_language=lang)
                    text = result["translatedText"]
                    translated_lines[lang].append(text)
                except Exception as e:
                    translated_lines[lang].append(f"[Error: {str(e)}]")

        # --- Rhythmic Enhancement + Fillers only in Blended Output ---
        enhanced_translations = {}
        syllable_data = {lang: [] for lang in languages}

        for lang in languages:
            enhanced_translations[lang] = []
            for i, line in enumerate(lines):
                translated = translated_lines[lang][i]
                if show_filler_toggle:
                    enhanced_line, _ = add_fillers_to_match(line, translated)
                else:
                    enhanced_line = translated
                enhanced_translations[lang].append(enhanced_line)
                syllable_data[lang].append(syllable_count(enhanced_line))

        # --- Blended Output Section ---
        st.subheader("🎶 Blended Output")
        for i, line in enumerate(lines):
            blend_line = []
            for lang in languages:
                blend_line.append(enhanced_translations[lang][i])
            st.write(f"**{i+1}.** " + " | ".join(blend_line))

        # --- Syllable Analysis Section ---
        st.subheader("📊 Syllable Analysis")
        for i, line in enumerate(lines):
            st.markdown(f"**Line {i+1}:** {line}")
            for lang in languages:
                s_count = syllable_data[lang][i]
                dot_vis = visualize_syllable_dots(s_count) if show_dot_toggle else ""
                st.markdown(f"• {lang.upper()} → {s_count} syllables {dot_vis}")
            st.markdown("---")

        # --- Optional Plotly Chart ---
        if show_chart_toggle:
            st.subheader("📈 Rhythm Difference Chart")
            fig = plot_syllable_difference_chart(lines, syllable_data)
            st.plotly_chart(fig, use_container_width=True)
