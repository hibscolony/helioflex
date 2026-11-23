import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.data_loader import POLICIES, table, saved
from src.ui import cards, header, series


def show():
    header(
        "Energy overview",
        "Energy command center",
        "Kitakyushu · 2020",
    )
    observed = table("measured_pv_load_hourly")
    left, right = st.columns([1, 2])
    policy = left.selectbox("Dispatch strategy", POLICIES, index=2)
    dispatch = saved(policy)
    lo, hi = dispatch.index[[0, -1]].date
    dates = right.date_input(
        "Analysis window",
        (lo, hi),
        min_value=observed.index.min().date(),
        max_value=observed.index.max().date(),
    )
    if len(dates) != 2:
        st.info("Choose an end date to complete the interval.")
        return
    start, end = map(str, dates)
    f = dispatch.loc[start:end]
    m = observed.loc[start:end]
    cards(
        [
            (
                "Solar generation",
                f"{m.pv_kw.sum():,.0f} kWh",
                "Measured",
            ),
            (
                "Campus consumption",
                f"{m.load_kw.sum():,.0f} kWh",
                "Measured",
            ),
        ]
    )
    if not f.empty:
        st.caption(
            f"Scenario coverage · {f.index.min()} through {f.index.max()} · {len(f):,} hourly records"
        )
        pv = f.pv_kwh.sum()
        utilization = (
            f"{100*(1-f.curtailment_kwh.sum()/pv):.2f}%"
            if pv
            else "Undefined (zero PV)"
        )
        cards(
            [
                (
                    "Grid import",
                    f"{f.grid_import_kwh.sum():,.1f} kWh",
                    policy + " · simulated",
                ),
                ("Solar utilization", utilization, "Scenario · includes charging"),
                (
                    "Peak grid demand",
                    f"{f.grid_import_kwh.max():,.0f} kW",
                    "Scenario · hourly mean",
                ),
                (
                    "Ending battery SOC",
                    f"{f.soc_kwh.iloc[-1]:,.1f} kWh",
                    "Scenario · stored energy",
                ),
                (
                    "Electricity cost",
                    f"IDR {f.bill_idr.sum():,.0f}",
                    "Hypothetical tariff",
                ),
                (
                    "Grid emissions",
                    f"{.7*f.grid_import_kwh.sum():,.0f} kg CO₂",
                    "Illustrative · 0.70 kg/kWh",
                ),
            ]
        )
    else:
        st.info(f"Dispatch records cover {lo} to {hi}.")
    st.subheader("Measured campus energy")
    a, b = st.columns(2)
    freq = a.selectbox("Aggregation", ["Daily", "Weekly", "Monthly"])
    mode = b.radio("Display", ["Line", "Bars"], horizontal=True)
    series(
        m.rename(columns={"pv_kw": "Solar generation", "load_kw": "Campus load"})
        .resample({"Daily": "D", "Weekly": "W", "Monthly": "ME"}[freq])
        .sum(),
        "kWh per period",
        mode,
    )
    if not f.empty:
        st.subheader("Scenario power flow")
        st.caption(
            "Energy delivered over the selected dispatch hours · kWh. Hover over a connection for its total."
        )
        fig = go.Figure(
            go.Sankey(
                valueformat=",.1f",
                valuesuffix=" kWh",
                node=dict(
                    label=["Solar PV", "Campus load", "Battery", "Grid", "Curtailment"],
                    color=["#108368", "#305c57", "#cf923b", "#6796ac", "#aaa69a"],
                ),
                link=dict(
                    source=[0, 0, 2, 3, 0],
                    target=[1, 2, 1, 1, 4],
                    value=[
                        f[["pv_kwh", "load_kwh"]].min(axis=1).sum(),
                        f.charge_kwh.sum(),
                        f.discharge_kwh.sum(),
                        f.grid_import_kwh.sum(),
                        f.curtailment_kwh.sum(),
                    ],
                ),
            )
        )
        st.plotly_chart(fig, width="stretch")
    with st.expander("Units and calculations"):
        st.write(
            "Each row represents one hour. Energy (kWh) equals mean power (kW) × 1 h. PV + import + discharge = load + charge + curtailment. Utilization = 100 × (generation − curtailment) / generation. Peak is the largest hourly grid import divided by 1 h. Cost sums hourly import × tariff. SOC is the final stored energy."
        )
