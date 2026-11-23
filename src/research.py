import pandas as pd
import plotly.express as px
import streamlit as st
from src.data_loader import DATA, table, provenance
from src.ui import cards, header, csv_button, COLORS

METRICS = {
    "Grid import (kWh)": "grid_import_kwh",
    "Peak grid demand (kW)": "peak_grid_kw",
    "Solar utilization (%)": "PV_utilization_pct",
    "Curtailment (kWh)": "curtailed_kwh",
    "Scenario bill (IDR)": "scenario_bill_idr",
    "Illustrative emissions (kg COâ‚‚)": "illustrative_grid_co2_kg",
}
LIMITS = "Rule-based control captures more surplus solar and yields the lowest scenario bill. HELIOFLEX follows a day-ahead plan whose charge and discharge targets can miss actual surplus or demand. Test intraday replanning and forecast uncertainty on additional years before drawing campus-wide conclusions."
METHOD = "Measurements come from Kitakyushu Science and Research Park in 2020. Hourly load and PV drive the experiment. After constructing lagged features, the notebook splits records chronologically into 70% training, 15% validation and 15% test. Validation MAE determines model selection. Models are refitted on training and validation data before held-out evaluation."
ASSUMPTIONS = "Expanded PV, battery storage, tariff and grid emissions are scenario assumptions. Storage charges only from surplus solar. The hypothetical bill includes energy charges at IDR 1,500/kWh off peak and 2,200/kWh during 17:00â€“21:59. Emissions equal grid import Ã— 0.70 kg COâ‚‚/kWh. Savings exclude capital costs."
PATHWAY = "Audit rooftop area and electrical limits, collect site tariffs and metering data, then compare controllers in shadow operation before a supervised hardware pilot."


def forecasting():
    header(
        "AI forecasting lab",
        "Day-ahead forecasts",
        "Compare validation rankings and held-out errors for the two measured signals.",
    )
    target = st.radio(
        "Forecast target",
        ["pv_kw", "load_kw"],
        format_func=lambda k: {"pv_kw": "Solar PV", "load_kw": "Campus load"}[k],
        horizontal=True,
    )
    data = table("02_forecast_comparison")
    ranks = (
        data[data.target == target]
        .sort_values("validation_MAE_kW")
        .reset_index(drop=True)
    )
    ranks.index += 1
    best = ranks.iloc[0]
    st.subheader(f"Validation selection Â· {best.model}")
    cards(
        [
            (c, f"{best[k]:.2f} {unit}", "Held-out test")
            for c, k, unit in [
                ("MAE", "MAE_kW", "kW"),
                ("RMSE", "RMSE_kW", "kW"),
                ("WAPE", "WAPE_pct", "%"),
            ]
        ]
    )
    st.dataframe(
        ranks.drop(columns="target").rename(
            columns={
                "MAE_kW": "Test MAE (kW)",
                "RMSE_kW": "Test RMSE (kW)",
                "WAPE_pct": "Test WAPE (%)",
                "validation_MAE_kW": "Validation MAE (kW)",
            }
        ),
        width="stretch",
    )
    st.image(
        str(DATA / f"03_forecast_{target}.png"),
        caption="Original Kaggle figure Â· first week of the held-out period",
    )
    with st.expander("Model selection and time split"):
        st.write(METHOD)
        p = provenance()
        for label, key in [
            ("Training", "train_range"),
            ("Validation", "valid_range"),
            ("Test", "test_range"),
        ]:
            st.caption(f"{label} Â· {' through '.join(p[key])}")
        st.write(
            "Calendar variables are known in advance. Both signals use 24-hour and 168-hour lags, and the rolling mean starts 24 hours back. The test period plays no role in model selection. PV persistence wins on validation MAE. Low total solar production makes WAPE sensitive to modest absolute errors."
        )


def comparison():
    header(
        "Experimental results",
        "Strategy comparison",
        "Three policies share the same measured test load, scaled PV profile and tariff schedule.",
    )
    data = table("05_strategy_comparison").set_index("strategy")
    labels = st.multiselect(
        "Metrics to compare",
        list(METRICS),
        default=["Grid import (kWh)", "Scenario bill (IDR)"],
    )
    if labels:
        selected = data[[METRICS[k] for k in labels]].copy()
        selected.columns = labels
        # Each facet has its own units and scale.
        melted = selected.reset_index().melt(id_vars="strategy", var_name="Metric")
        fig = px.bar(
            melted,
            x="Metric",
            y="value",
            color="strategy",
            facet_col="Metric",
            facet_col_wrap=2,
            barmode="group",
            color_discrete_sequence=COLORS,
        )
        fig.update_yaxes(matches=None, showticklabels=True, title=None)
        fig.update_xaxes(matches=None, showticklabels=False, title=None)
        fig.for_each_annotation(lambda a: a.update(text=a.text.replace("Metric=", "")))
        st.plotly_chart(fig, width="stretch")
    st.dataframe(
        data[list(METRICS.values())]
        .rename(columns={v: k for k, v in METRICS.items()})
        .T,
        width="stretch",
    )
    a, b = data.loc["HELIOFLEX"], data.loc["Rule-based"]
    cards(
        [
            (k, f"{100*(a[v]/b[v]-1):+.3f}%", "HELIOFLEX relative to Rule-based")
            for k, v in list(METRICS.items())
            if b[v] != 0
        ]
    )
    st.subheader("Research Findings & Limitations")
    st.write(LIMITS)


def report():
    header(
        "Research impact & report",
        "Experiment record",
        "EcoVibes 2026 Â· National Scientific Writing Competition",
    )
    p = provenance()
    citations = f"[Figshare dataset](https://doi.org/{p['dataset_doi']}) Â· [Scientific Data paper](https://doi.org/{p['paper_doi']})"
    tables = {
        label: table(key)
        for label, key in [
            ("Data quality", "data_quality_summary"),
            ("Forecast evaluation", "02_forecast_comparison"),
            ("Energy performance", "05_strategy_comparison"),
            ("Sensitivity analysis", "08_sensitivity"),
        ]
    }
    st.subheader("Methodology and provenance")
    st.write(METHOD)
    st.markdown(citations)
    for label, df in tables.items():
        with st.expander(label, expanded=label == "Data quality"):
            st.dataframe(df, hide_index=True, width="stretch")
            csv_button("Download " + label.lower() + " CSV", df, label + ".csv")
    st.image(
        str(DATA / "07_grid_profile.png"),
        caption="Archived experiment Â· grid import under the three policies",
    )
    st.subheader("Assumptions and limitations")
    st.write(ASSUMPTIONS)
    st.write(LIMITS)
    st.subheader("Campus implementation pathway")
    st.write(PATHWAY)
    report_text = "\n\n".join(
        ["# HELIOFLEX research report", METHOD, citations, ASSUMPTIONS, LIMITS, PATHWAY]
        + [f"## {k}\n\n```csv\n{v.to_csv(index=False)}```" for k, v in tables.items()]
    )
    st.download_button(
        "Download Research Report",
        report_text,
        "HELIOFLEX-research-report.md",
        "text/markdown",
    )
