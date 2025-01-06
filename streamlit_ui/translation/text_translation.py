import streamlit as st

from core.ai_core.translation.language import Language
from core.ai_core.translation.text_translator import TextTranslator


def translate_text(source_text, source_lang, target_lang):
    """Translates source_text from source_lang to target_lang using TextTranslator."""
    translator = TextTranslator(source_lang, target_lang)
    return translator.translate(source_text)


def render_text_translation_page():
    st.title("Text Translation")

    translated_text = ""

    # Create columns for layout
    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.subheader("Source Text")
        source_text = st.text_area("Enter text to translate:", height=300)
        uploaded_files = st.file_uploader("Upload files for translation", accept_multiple_files=True)

    with col2:
        st.subheader("Translate")
        # Create translation buttons
        if st.button("日➡︎中"):
            translated_text = translate_text(
                source_text, source_lang=Language.JAPANESE, target_lang=Language.CHINESE
            )
            st.session_state.translated_text = translated_text
        if st.button("日➡︎英"):
            translated_text = translate_text(
                source_text, source_lang=Language.JAPANESE, target_lang=Language.ENGLISH
            )
            st.session_state.translated_text = translated_text
        if st.button("中➡︎日"):
            translated_text = translate_text(
                source_text, source_lang=Language.CHINESE, target_lang=Language.JAPANESE
            )
            st.session_state.translated_text = translated_text
        if st.button("中➡︎英"):
            translated_text = translate_text(
                source_text, source_lang=Language.CHINESE, target_lang=Language.ENGLISH
            )
            st.session_state.translated_text = translated_text
        if st.button("英➡︎日"):
            translated_text = translate_text(
                source_text, source_lang=Language.ENGLISH, target_lang=Language.JAPANESE
            )
            st.session_state.translated_text = translated_text
        if st.button("英➡︎中"):
            translated_text = translate_text(
                source_text, source_lang=Language.ENGLISH, target_lang=Language.CHINESE
            )

    with col3:
        st.subheader("Translated Text")
        if translated_text:
            st.text_area(
                "Translation Result:",
                value=translated_text,
                height=300,
                disabled=False,
            )
        else:
            st.text_area("Translation Result:", value="", height=300, disabled=True)
