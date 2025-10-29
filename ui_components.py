import streamlit as st
import plotly.graph_objects as go

def init_logging_sidebar():
    """Create a place in the sidebar to display logs. Returns a placeholder object we can update."""
    st.sidebar.header("🚦 Logs")
    log_placeholder = st.sidebar.empty()
    # start empty
    log_placeholder.text_area("log_area", value="", height=200)
    return log_placeholder

def update_logs(log_placeholder, text):
    """Update the log text area in the sidebar."""
    try:
        # Streamlit text_area cannot be programmatically updated easily; re-render placeholder
        log_placeholder.text_area("log_area", value=text, height=200)
    except Exception:
        # fallback
        log_placeholder.write(text)

def plot_syllable_comparison_tabs(stats_by_lang):
    """
    stats_by_lang: dict mapping language name -> dict with keys:
        syllables_orig, syllables_trans_before, syllables_trans_after
    Creates a tab per language with a compact Plotly chart.
    """
    if not stats_by_lang:
        return
    tabs = st.tabs(list(stats_by_lang.keys()))
    for tab, (lang_name, stats) in zip(tabs, stats_by_lang.items()):
        with tab:
            categories = ["Original", f"{lang_name} (clean)", f"{lang_name} (enhanced)"]
            values = [stats.get("syllables_orig", 0),
                      stats.get("syllables_trans_before", 0),
                      stats.get("syllables_trans_after", 0)]
            colors = []
            for v in values:
                diff = abs(v - stats.get("syllables_orig", 0))
                colors.append("#2ecc71" if diff == 0 else "#f1c40f" if diff <= 2 else "#e74c3c")
            fig = go.Figure([go.Bar(x=categories, y=values, marker_color=colors, text=values, textposition="auto")])
            fig.update_layout(title=f"Syllable Count — {lang_name}", yaxis_title="Syllable count", height=360)
            st.plotly_chart(fig, use_container_width=True)
