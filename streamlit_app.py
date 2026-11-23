import streamlit as st
from src import overview, research, twin, iot_replay
from src.data_loader import table

st.set_page_config(page_title="HELIOFLEX · Campus Energy", page_icon="☀️", layout="wide")
pages = {
    "Energy overview": overview.show,
    "AI forecasting lab": research.forecasting,
    "Digital twin simulator": twin.show,
    "Strategy comparison": research.comparison,
    "Virtual IoT monitoring": iot_replay.show,
    "Research impact & report": research.report,
}
with st.sidebar:
    st.markdown("## ☀ HELIOFLEX")
    st.caption("Intelligent Campus Renewable Energy Management")
    st.divider()
    page = st.radio("Workspace", pages)
    st.divider()
    st.caption("EcoVibes 2026 · Research prototype")
    with st.expander("About HELIOFLEX"):
        st.caption("AI-Powered Solar Energy Orchestration & Digital Twin")
try:
    observations = table("measured_pv_load_hourly")
    st.sidebar.success(f"Historical dataset · {len(observations):,} hours")
    pages[page]()
except (OSError, KeyError, ValueError) as exc:
    st.error(
        f"Unable to display research records. Verify the bundled data files. Details: {exc}"
    )
