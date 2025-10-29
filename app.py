import streamlit as st
import concurrent.futures
import logging
import io
import base64

from translate_utils import translate_text, translate_client, get_translate_client  # translate_client optionally used
from rhythm_utils import rhythmic_translation_enhancement, count_syllables, clean_text, build_fillers
from blend_utils import interleave_words, phrase_swap, last_word_swap, remove_consecutive_duplicates
from ui_components import init_logging_sidebar, update_logs, plot_syllable_comparison_tabs

from gtts import gTTS
import tempfile

# Setup basic logging that writes to a buffer we can show in the sidebar
log_stream = io.StringIO()
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(log_stream)])
logger = logging.getLogger("melosphere")

# Cache translate client initialization (ensures get_translate_client executed)
_ = get_translate_client()

# ------------------------
# Cached TTS generator
# ------------------------
@st.cache_data(show_spinner=False)
def generate_tts_audio_cached(text, lang_code):
    """Generate and cache TTS audio as base64 audio tag (cached by Streamlit)."""
    try:
        tts = gTTS(text=text, lang=lang_code)
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_path.name)
        with open(temp_path.name, "rb") as f:
            audio_bytes = f.read()
        b64 = base64.b64encode(audio_bytes).decode()
        audio_html = f'<audio controls src="data:audio/mp3;base64,{b64}"></audio>'
        logger.info(f"TTS generated for [{lang_code}] text length={len(text)}")
        return audio_html
    except Exception as e:
        logger.exception("Audio generation failed.")
        return f"<i>Audio unavailable: {e}</i>"

# ------------------------
# App UI
# ------------------------
def main():
    st.set_page_config(page_title="Melosphere — Polyglot Blending", layout="wide")
    st.title("🎛️ Melosphere — Polyglot Lyric Blending")

    # Logging sidebar
    log_placeholder = init_logging_sidebar()

    col1, col2 = st.columns([2, 1])
    with col1:
        lyric_line = st.text_area("Enter your lyric line (English):", height=80)
        # quick examples
        if st.button("Try example: 'I feel the sun'"):
            lyric_line = "I feel the sun inside my bones."
    with col2:
        available_languages = {
            "Spanish": "es", "Kannada": "kn", "Tamil": "ta", "Malayalam": "ml", "Hindi": "hi",
            "Telugu": "te", "Japanese": "ja", "French": "fr", "Portuguese": "pt",
            "German": "de", "Korean": "ko"
        }
        selected = st.multiselect("Select 2+ target languages:", list(available_languages.keys()), default=["Spanish", "Hindi"])
        mode = st.selectbox("Blending mode:", ["Interleave Words", "Phrase Swap", "Last-Word Swap"])
        enhance_rhythm = st.checkbox("✨ Rhythmic Enhancement", value=True)
        fillers_in_blend_only = st.checkbox("Show fillers only in blended output", value=True)
        show_plot = st.checkbox("Show syllable comparison chart", value=False)
        show_dots = st.checkbox("Show syllable dots visual", value=False)
        show_syllables = st.checkbox("Show syllable hints / rhythm warnings", value=True)
        show_rhymes = st.checkbox("Show English rhymes for the last word", value=True)

    if not lyric_line or not selected:
        st.info("Enter a lyric and select at least one target language.")
        return

    # Normalize input once
    lyric_line_clean = clean_text(lyric_line)

    # Prepare language codes
    tgt_codes = [available_languages[l] for l in selected]

    # Concurrent translations
    translations_clean = {}
    translations_enhanced = {}
    overall_stats = {}

    # Submit translation tasks concurrently
    def _translate_for_lang(lang_name, code):
        txt = translate_text(lyric_line_clean, code)
        if enhance_rhythm:
            enhanced, syllables_orig, syllables_trans_before, syllables_trans_after, diff = rhythmic_translation_enhancement(
                lyric_line_clean, txt)
        else:
            enhanced = txt
            syllables_orig = count_syllables(lyric_line_clean, "en")
            syllables_trans_before = count_syllables(txt, code)
            syllables_trans_after = syllables_trans_before
            diff = syllables_orig - syllables_trans_before
        return (lang_name, code, txt, enhanced, syllables_orig, syllables_trans_before, syllables_trans_after, diff)

    logger.info("Starting translations (concurrent)")
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(tgt_codes))) as executor:
        futures = [executor.submit(_translate_for_lang, lang_name, code) for lang_name, code in zip(selected, tgt_codes)]
        for fut in concurrent.futures.as_completed(futures):
            try:
                (lang_name, code, txt, enhanced, syllables_orig, syllables_trans_before, syllables_trans_after, diff) = fut.result()
                translations_clean[lang_name] = txt
                translations_enhanced[lang_name] = enhanced
                overall_stats[lang_name] = {
                    "syllables_orig": syllables_orig,
                    "syllables_trans_before": syllables_trans_before,
                    "syllables_trans_after": syllables_trans_after,
                    "diff": diff,
                    "code": code
                }
                logger.info(f"Translated {lang_name} ({code})")
            except Exception as e:
                logger.exception("Translation future failed.")

    # Render translations
    st.subheader("Translations")
    trans_cols = st.columns(len(selected))
    for col, lang_name in zip(trans_cols, selected):
        with col:
            code = available_languages[lang_name]
            st.markdown(f"**{lang_name} ({code})**")
            st.write(translations_clean.get(lang_name, ""))
            if show_syllables:
                stats = overall_stats.get(lang_name, {})
                st.caption(f"Syllables — orig: {stats.get('syllables_orig')}, clean: {stats.get('syllables_trans_before')}, enhanced: {stats.get('syllables_trans_after')}")

    # Blended output
    st.subheader("Blended Outputs")
    translations_list_for_blend = [translations_enhanced[name] for name in selected]
    if mode == "Interleave Words":
        blended = interleave_words(lyric_line_clean, translations_list_for_blend)
    elif mode == "Phrase Swap":
        blended = phrase_swap(lyric_line_clean, translations_list_for_blend)
    else:
        blended = last_word_swap(lyric_line_clean, translations_list_for_blend)

    blended = remove_consecutive_duplicates(blended)

    # Optionally show fillers in blended only
    if fillers_in_blend_only:
        # regenerate fillers deterministically for the blended text if needed (keeps behavior)
        st.info(f"**Blended lyric preview:**\n{blended}")
    else:
        st.info(f"**Blended lyric preview:**\n{blended}")

    # Syllable charts in tabs
    if show_plot:
        plot_syllable_comparison_tabs(overall_stats)

    # Pronunciation Guide
    st.subheader("🎙️ Pronunciation Guide")
    show_simple = st.checkbox("See simplified style (default = IPA)", value=False, key="pron_simple")
    for lang_name in selected:
        code = available_languages[lang_name]
        text = translations_clean[lang_name]
        # For compatibility with previous interface call, we re-use a simple ipa function from earlier codebase logic.
        # Keep behavior unchanged: use transliteration heuristics in rhythm_utils if needed — here we keep it simple.
        # We'll show TTS
        st.markdown(f"**{lang_name} pronunciation:**")
        # lightweight pronunciation display - re-using count_syllables as placeholder for earlier get_pronunciation behavior
        st.markdown(f"_(approx. syllables: {overall_stats[lang_name].get('syllables_trans_after')})_")
        audio_html = generate_tts_audio_cached(text, code)
        st.markdown(audio_html, unsafe_allow_html=True)

    # Update logs into sidebar
    log_text = log_stream.getvalue()
    update_logs(log_placeholder, log_text)

if __name__ == "__main__":
    main()
