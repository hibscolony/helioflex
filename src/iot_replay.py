import streamlit as st
from src.data_loader import table
from src.ui import cards, header, series


def show():
    header(
        "Virtual IoT monitoring",
        "Historical telemetry",
        "Virtual IoT Replay — Research Simulation",
    )
    df = table("09_iot_virtual_telemetry")
    measured = table("measured_pv_load_hourly")
    state = st.session_state
    state.setdefault("cursor", 0)
    state.setdefault("playing", False)
    a, b, c, d = st.columns(4)
    speed = a.selectbox(
        "Replay rate", [1, 4, 12, 24], format_func=lambda x: f"{x} hours / second"
    )
    if b.button("Play"):
        if state.cursor == len(df) - 1:
            state.cursor = 0
        state.playing = True
    if c.button("Pause"):
        state.playing = False
    if d.button("Reset"):
        state.cursor = 0
        state.playing = False

    @st.fragment(run_every=1 if state.playing else None)
    def panel():
        pos = state.cursor
        row = df.iloc[pos]
        ts = df.index[pos]
        st.subheader(ts.strftime("%d %B %Y · %H:%M"))
        st.caption(
            f"Virtual sensor record {pos+1} of {len(df)} · {row.topic} · {row.controller}"
        )
        cards(
            [
                (
                    "Solar PV",
                    f"{measured.at[ts,'pv_kw']:,.1f} kW",
                    "Historical measurement",
                ),
                (
                    "Campus load",
                    f"{row.load_kw_measured:,.1f} kW",
                    "Historical measurement",
                ),
                ("Grid import", f"{row.grid_import_kw_simulated:,.1f} kW", "Simulated"),
                ("Battery SOC", f"{row.battery_soc_pct_simulated:.1f}%", "Simulated"),
            ]
        )
        if row.battery_soc_pct_simulated <= 10:
            st.warning("Simulated alert · battery at the 10% operating reserve.")
        else:
            st.info("Simulated status · battery above operating reserve.")
        window = df.iloc[max(0, pos - 47) : pos + 1]
        series(
            window[
                ["pv_kw_scenario", "load_kw_measured", "grid_import_kw_simulated"]
            ].rename(
                columns={
                    "pv_kw_scenario": "Scaled PV",
                    "load_kw_measured": "Measured load",
                    "grid_import_kw_simulated": "Simulated grid",
                }
            ),
            "kW",
            "Bars" if pos == 0 else "Line",
        )
        st.subheader("Historical event stream")
        st.dataframe(window.tail(8).iloc[::-1], width="stretch")
        if state.playing:
            if pos == len(df) - 1:
                state.playing = False
                st.rerun()
            else:
                state.cursor = min(len(df) - 1, pos + speed)

    panel()
