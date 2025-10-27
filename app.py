import streamlit as st
import re
from deep_translator import GoogleTranslator
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# ---------------------------
# Core Translation Function
# ---------------------------
def translate(text, tgt_lang_code):
    try:
        return GoogleTranslator(source='auto', target=tgt_lang_code).translate(text)
    except Exception as e:
        return f"Error: {e}"

# ---------------------------
# Syllable Count for Indic Languages
# ---------------------------
def count_indic_syllables(word):
    vowels = re.findall(r'[\u0B05-\u0B14\u0B3E-\u0B4C\u0B60-\u0B61\u0905-\u090F\u093E-\u094C]', word)
    return max(1, len(vowels))

def count_total_syllables(line):
    words = line.strip().split()
    return sum(count_indic_syllables(w) for w in words)

# ---------------------------
# Rhyming in Indic Languages
# ---------------------------
def last_syllable(word):
    word = word.strip()
    return word[-2:]  # crude last 2 chars for rhyme

def find_rhymes_indic(word, vocab_list):
    target = last_syllable(word)
    rhymes = [w for w in vocab_list if last_syllable(w) == target and w != word]
    return rhymes[:10]

# Example small vocabulary for Tamil
TAMIL_VOCAB = ["காதல்", "பாதல்", "நாதல்", "மாதல்", "வாதல்", "சாதல்"]

# ---------------------------
# Rhythm Adjustment
# ---------------------------
def rhythmic_adjustment_indic(translated_line, target_syllables):
    words = translated_line.strip().split()
    total_syl = sum(count_indic_syllables(w) for w in words)

    if total_syl < target_syllables:
        words += ["…"] * (target_syllables - total_syl)
    elif total_syl > target_syllables:
        while total_syl > target_syllables and len(words) > 1:
            removed = words.pop()
            total_syl -= count_indic_syllables(removed)
    return ' '.join(words)

# ---------------------------
# Pronunciation Guide
# ---------------------------
def pronunciation_guide_indic(line, lang='ta'):
    if lang == 'ta':
        return transliterate(line, sanscript.TAMIL, sanscript.ITRANS)
    elif lang == 'hi':
        return transliterate(line, sanscript.DEVANAGARI, sanscript.ITRANS)
    elif lang == 'kn':
        return transliterate(line, sanscript.KANNADA, sanscript.ITRANS)
    elif lang == 'ml':
        return transliterate(line, sanscript.MALAYALAM, sanscript.ITRANS)
    elif lang == 'te':
        return transliterate(line, sanscript.TELUGU, sanscript.ITRANS)
    else:
        return line

# ---------------------------
# Streamlit UI
# ---------------------------
def main():
    st.title("Melosphere AI - Indian Language Lyric Translator 🎵")

    lyric_input = st.text_area("Enter your English lyric line or full song:")

    languages = {
        "Tamil": "ta",
        "Hindi": "hi",
        "Kannada": "kn",
        "Malayalam": "ml",
        "Telugu": "te",
    }

    tgt_lang = st.selectbox("Select Target Language:", list(languages.keys()))

    if lyric_input:
        # Step 1: Translate
        translated_line = translate(lyric_input, languages[tgt_lang])
        st.subheader(f"{tgt_lang} Translation:")
        st.write(translated_line)

        # Step 2: Rhythmic Alignment
        total_syllables = count_total_syllables(lyric_input)
        rhythmic_line = rhythmic_adjustment_indic(translated_line, total_syllables)
        st.subheader("Rhythmic-Aligned Lyric:")
        st.write(rhythmic_line)

        # Step 3: Rhymes (using small vocab)
        last_word = rhythmic_line.strip().split()[-1]
        if tgt_lang == "Tamil":
            rhymes = find_rhymes_indic(last_word, TAMIL_VOCAB)
            st.subheader("Rhymes:")
            if rhymes:
                st.write(", ".join(rhymes))
            else:
                st.write("No rhymes found.")

        # Step 4: Pronunciation Guide
        pron_guide = pronunciation_guide_indic(rhythmic_line, lang=languages[tgt_lang])
        st.subheader("Pronunciation Guide (ITRANS):")
        st.write(pron_guide)

if __name__ == "__main__":
    main()
