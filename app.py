import streamlit as st
import requests, re, random
import pronouncing
from transformers import MBartForConditionalGeneration, MBart50TokenizerFast
import torch

# ------------------------------------------------------------
# Load multilingual model once
# ------------------------------------------------------------
@st.cache_resource
def load_mbart_model():
    model_name = "facebook/mbart-large-50-many-to-many-mmt"
    tokenizer = MBart50TokenizerFast.from_pretrained(model_name)
    model = MBartForConditionalGeneration.from_pretrained(model_name)
    return tokenizer, model

tokenizer, model = load_mbart_model()

# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------
def translate_with_model(text, src_lang, tgt_lang):
    """Translate a sentence using mBART-50."""
    try:
        tokenizer.src_lang = src_lang
        inputs = tokenizer(text, return_tensors="pt")
        generated_tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.lang_code_to_id[tgt_lang],
            max_length=256
        )
        return tokenizer.decode(generated_tokens[0], skip_special_tokens=True)
    except Exception as e:
        return text

def clean_text(line):
    line = re.sub(r"\s+([.,!?])", r"\1", line)
    return re.sub(r"\s+", " ", line).strip()

def get_rhymes(word):
    try:
        resp = requests.get(f"https://api.datamuse.com/words?rel_rhy={word}&max=10")
        if resp.status_code == 200:
            return [x["word"] for x in resp.json()]
    except:
        pass
    return []

def count_syllables(word):
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    return sum(1 for c in word.lower() if c in "aeiou")

# ------------------------------------------------------------
# Polyglot blending using mBART
# ------------------------------------------------------------
def mbart_polyglot_blend(text, src_lang, tgt_langs, creativity=0.5):
    """
    Sentence-level polyglot blending with mBART.
    Each sentence can be rendered in a different language depending on creativity.
    """
    sentences = re.split(r"([.?!])", text)
    blended = []

    for i in range(0, len(sentences), 2):
        sentence = sentences[i].strip()
        if not sentence:
            continue
        punct = sentences[i + 1] if i + 1 < len(sentences) else ""

        # Decide language
        if random.random() < creativity:
            tgt = random.choice(tgt_langs)
        else:
            tgt = src_lang

        translated = translate_with_model(sentence, src_lang, tgt)
        blended.append(translated + punct)

    return clean_text(" ".join(blended))

# ------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------
def main():
    st.set_page_config(page_title="Melosphere AI", page_icon="🎶")
    st.title("🎵 Melosphere AI — Lyrics Without Limits 🌍")

    st.markdown("""
    *AI-powered multilingual lyric writing and blending, backed by Facebook mBART-50.*  
    """)

    st.divider()
    st.header("Phase 1 — Rhyme & Translation Assistant")

    lyric_line = st.text_input("🎤 Enter your lyric line (English):")

    languages = {
        "English": "en_XX",
        "Spanish": "es_XX",
        "Hindi": "hi_IN",
        "Tamil": "ta_IN",
        "French": "fr_XX",
        "German": "de_DE",
        "Japanese": "ja_XX",
        "Telugu": "te_IN",
        "Malayalam": "ml_IN",
    }

    tgt_lang = st.selectbox("🌐 Translate to:", list(languages.keys()))

    if lyric_line:
        words = lyric_line.strip().split()
        last = words[-1].lower()
        rhymes = get_rhymes(last)
        if rhymes:
            st.write(f"**Rhymes for '{last}':** {', '.join(rhymes)}")
        else:
            st.write(f"No rhymes found for '{last}'.")

        syllables = {w: count_syllables(w) for w in words}
        st.write("🪶 **Syllables per word:**", syllables)
        st.write("🔢 **Total syllables:**", sum(syllables.values()))

        translated = translate_with_model(
            lyric_line, "en_XX", languages[tgt_lang]
        )
        st.success(f"**{tgt_lang} Translation:** {translated}")

    st.divider()
    st.header("Phase 2 — mBART Polyglot Lyric Blending 🌐")

    blend_langs = st.multiselect(
        "Select blend languages:",
        list(languages.keys()),
        default=["English", "Spanish", "Hindi", "Tamil"],
    )

    creativity = st.slider(
        "🎨 Creativity (0 = Mostly English, 1 = Fully Multilingual)",
        0.0, 1.0, 0.6, 0.1
    )

    if lyric_line and blend_langs:
        code_list = [languages[l] for l in blend_langs]
        blended = mbart_polyglot_blend(lyric_line, "en_XX", code_list, creativity)
        st.write("### 🎶 **Blended Lyric Line:**")
        st.success(blended)
        st.caption("Higher creativity → more multilingual variation per line.")

    st.divider()
    st.markdown("""
    🚀 **Next Phases**
    - Phase 3 → Rhythmic Translation Enhancement  
    - Phase 4 → Pronunciation & Emotion Adaptation  
    - Phase 5 → AI Rhyme & Metaphor Engine + DAW Integration  
    """)

if __name__ == "__main__":
    main()
