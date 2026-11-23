import pandas as pd
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
        direct = f[["pv_kwh", "load_kwh"]].min(axis=1).sum()
        groups = [
            (
                "Campus supply",
                "Campus demand",
                f.load_kwh.sum(),
                [
                    ("Grid → Campus", f.grid_import_kwh.sum(), "#497aa6"),
                    ("Solar PV → Campus", direct, "#16846e"),
                    ("Battery → Campus", f.discharge_kwh.sum(), "#8a66aa"),
                ],
            ),
            (
                "Solar allocation",
                "Scenario PV",
                f.pv_kwh.sum(),
                [
                    ("Solar PV → Campus", direct, "#16846e"),
                    ("Solar PV → Battery", f.charge_kwh.sum(), "#c58a21"),
                    ("Curtailed solar", f.curtailment_kwh.sum(), "#b46d51"),
                ],
            ),
        ]
        panels = []
        for title, basis, total, routes in groups:
            rows = []
            for label, energy, color in routes:
                share = energy / total * 100 if total else 0
                percentage = f"{share:.2f}%" if total else "—"
                rows.append(
                    f"""
                    <div class="hf-route"><div><b>{label}</b><span>{energy:,.1f} kWh</span></div>
                    <div><i aria-hidden="true"><em style="width:{share:.8f}%;background:{color}"></em></i>
                    <small>{percentage}</small></div></div>"""
                )
            panels.append(
                f'<section><h4>{title}</h4><p>{basis} · {total:,.1f} kWh</p>{"".join(rows)}</section>'
            )
        st.html(
            """
            <style>
            .hf-flows{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:16px}
            .hf-flows section{background:#f6faf8;border:1px solid #d4e5df;border-radius:16px;padding:20px;color:#193b32}
            .hf-flows h4{font-size:1.15rem;margin:0;padding:0}
            .hf-flows p{font-size:.84rem;color:#4b655b;margin:3px 0 18px}
            .hf-route+.hf-route{margin-top:16px}
            .hf-route div{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
            .hf-route b,.hf-route span{font-size:.9rem}
            .hf-route span,.hf-route small{font-variant-numeric:tabular-nums}
            .hf-route i{flex:1;height:6px;background:#dde8e4;border-radius:5px;overflow:hidden}
            .hf-route em{display:block;height:100%;border-radius:5px}
            .hf-route small{font-size:.77rem;color:#4b655b}
            </style><div class="hf-flows">"""
            + "".join(panels)
            + "</div>"
        )
    with st.expander("Units and calculations"):
        st.write(
            "Each row represents one hour. Energy (kWh) equals mean power (kW) × 1 h. PV + import + discharge = load + charge + curtailment. Utilization = 100 × (generation − curtailment) / generation. Peak is the largest hourly grid import divided by 1 h. Cost sums hourly import × tariff. SOC is the final stored energy."
        )
