import streamlit as st
from src import research, twin, hybrid_research
from src.data_loader import table

st.set_page_config(page_title="HELIOFLEX · Campus Energy", page_icon="☀️", layout="wide")
pages = {
    "Energy overview": hybrid_research.overview,
    "AI forecasting lab": research.forecasting,
    "Digital twin simulator": hybrid_research.sensitivity,
    "Strategy comparison": hybrid_research.comparison,
    "Virtual IoT monitoring": hybrid_research.telemetry,
    "Research impact & report": hybrid_research.report,
    "Initial-controller sandbox (archive)": twin.show,
}
with st.sidebar:
    st.markdown("## ☀ HELIOFLEX")
    st.caption("Intelligent Campus Renewable Energy Management")
    st.divider()
    page = st.radio("Workspace", pages)
    st.divider()
    st.caption("EcoVibes 2026 · Research prototype")
    with st.expander("About HELIOFLEX"):
        st.caption("Hybrid predictive control & digital twin · research simulation")
try:
    observations = table("measured_pv_load_hourly")
    st.sidebar.success(f"Historical dataset · {len(observations):,} hours")
    if page == "Initial-controller sandbox (archive)":
        st.warning("Exploratory sandbox uses the initial controller, not the HELIOFLEX hybrid benchmark. Its output must not be presented as the latest research results.")
    pages[page]()
except (OSError, KeyError, ValueError) as exc:
    st.error(f"Unable to display research records. Verify the bundled data files. Details: {exc}")
