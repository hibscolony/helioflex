import streamlit as st
from src.digital_twin import dispatch, summarize
from src.data_loader import table, provenance, POLICIES
from src.ui import cards, series, header


def show():
    header(
        "Digital twin simulator",
        "Dispatch simulator",
        "Run the notebook controller on measured test-period load and PV with the selected day-ahead forecasts.",
    )
    p = provenance()
    with st.form("dispatch_settings"):
        strategy = st.selectbox("Controller", POLICIES, index=2)
        a, b, c = st.columns(3)
        scale = a.number_input("PV multiplier (×)", 0.0, 200.0, 50.0)
        cap = b.number_input(
            "Battery capacity (kWh)",
            0.0,
            100000.0,
            p["battery_kwh_assumed"],
            format="%.4f",
        )
        power = c.number_input(
            "Charge/discharge limit (kW)",
            0.0,
            10000.0,
            p["battery_kw_assumed"],
            format="%.4f",
        )
        initial = a.slider("Initial SOC (%)", 10, 90, 10)
        peak = b.number_input("Peak tariff (IDR/kWh)", 0.0, 100000.0, 2200.0)
        off = c.number_input("Off-peak tariff (IDR/kWh)", 0.0, 100000.0, 1500.0)
        st.caption(
            "Storage operates between 10% and 90% SOC at 95% efficiency in each direction. Baseline uses zero storage. Peak hours are 17:00–21:59."
        )
        run = st.form_submit_button("Run Simulation", type="primary")
    if run:
        f = table("twin_inputs")
        if strategy == "Baseline PV-only":
            cap = 0.0
        with st.spinner("Calculating hourly dispatch…"):
            out = dispatch(f, strategy, scale, cap, power, initial / 100, peak, off)
            baseline = dispatch(f, "Baseline PV-only", scale, 0, 0, 0.1, peak, off)
        st.session_state.scenario = (
            out,
            summarize(out, strategy, scale, cap),
            baseline.bill_idr.sum(),
            f"{strategy} · {scale:g}× PV · {cap:,.2f} kWh · {power:g} kW · initial SOC {initial}% · tariffs {off:g}/{peak:g} IDR/kWh",
        )
    if "scenario" not in st.session_state:
        st.info(
            "Run the simulation to calculate a scenario across the held-out test period."
        )
        return
    out, r, base, settings = st.session_state.scenario
    st.subheader("Simulation results")
    st.caption(settings)
    cards(
        [
            ("Grid import", f"{r['grid_import_kwh']:,.1f} kWh", "Simulated"),
            (
                "PV utilization",
                (
                    f"{r['PV_utilization_pct']:.2f}%"
                    if r["scenario_pv_generation_kwh"]
                    else "Undefined"
                ),
                "Scenario generation",
            ),
            ("Curtailment", f"{r['curtailed_kwh']:,.1f} kWh", "Unused solar"),
            ("Peak demand", f"{r['peak_grid_kw']:,.1f} kW", "Grid import"),
            ("Scenario bill", f"IDR {r['scenario_bill_idr']:,.0f}", "Energy charges"),
            (
                "Bill savings",
                f"{100*(1-r['scenario_bill_idr']/base):.3f}%" if base else "Undefined",
                "Against PV-only at identical tariffs and PV scale",
            ),
        ]
    )
    series(out[["soc_kwh"]].rename(columns={"soc_kwh": "Stored energy"}), "kWh")
