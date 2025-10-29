import streamlit as st
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
import logging

@st.cache_resource
def get_translate_client():
    """Initialize and cache Translate client (reads Streamlit secrets)."""
    try:
        credentials_info = st.secrets["gcp_service_account"]
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = translate.Client(credentials=credentials)
        logging.getLogger(__name__).info("Google Translate client initialized.")
        return client
    except Exception as e:
        logging.getLogger(__name__).exception("Google Translate API initialization error.")
        return None

translate_client = get_translate_client()

def translate_text(text, target_lang):
    """Translate text using cached translate_client. Returns translated string or error string."""
    if not translate_client:
        return "⚠️ Translation client not initialized. Check your credentials in Streamlit secrets."
    try:
        result = translate_client.translate(text, target_language=target_lang)
        return result.get("translatedText", "")
    except Exception as e:
        logging.getLogger(__name__).exception("Error during translation call.")
        return f"Error during translation: {e}"
