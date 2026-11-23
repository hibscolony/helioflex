import json
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "helioflex_outputs"
POLICIES = {
    "Baseline PV-only": "Baseline_PV_only",
    "Rule-based": "Rule_based",
    "HELIOFLEX": "HELIOFLEX",
}
SUMMARY = "strategy pv_scale battery_kwh observed_load_kwh scenario_pv_generation_kwh grid_import_kwh peak_grid_kw curtailed_kwh PV_utilization_pct grid_displacement_pct scenario_bill_idr illustrative_grid_co2_kg"
FIELDS = {
    "measured_pv_load_hourly": "timestamp pv_kw load_kw",
    "02_forecast_comparison": "target model validation_MAE_kW MAE_kW RMSE_kW WAPE_pct",
    "05_strategy_comparison": SUMMARY,
    "08_sensitivity": SUMMARY,
    "data_quality_summary": "value",
    "twin_inputs": "timestamp pv_kw_measured load_kw_measured pv_kw_forecast load_kw_forecast",
    "09_iot_virtual_telemetry": "timestamp pv_kw_scenario load_kw_measured grid_import_kw_simulated battery_soc_pct_simulated controller sensor_source topic",
}
for stem in POLICIES.values():
    FIELDS["04_dispatch_" + stem] = (
        "timestamp pv_kwh load_kwh grid_import_kwh curtailment_kwh charge_kwh discharge_kwh soc_kwh tariff_idr_per_kwh bill_idr"
    )


@st.cache_data(show_spinner=False)
def table(name):
    if name == "09_iot_virtual_telemetry":
        df = pd.read_json(DATA / (name + ".jsonl"), lines=True)
    else:
        path = ROOT / "data" if name == "twin_inputs" else DATA
        df = pd.read_csv(path / (name + ".csv"))
    missing = set(FIELDS[name].split()) - set(df)
    if missing or df.empty or df.isna().any().any():
        raise ValueError(
            f"{name} is empty, incomplete, or missing fields {sorted(missing)}"
        )
    if "timestamp" in df:
        df["timestamp"] = pd.to_datetime(df.timestamp, errors="raise")
        df = df.set_index("timestamp").sort_index()
        if (
            df.index.has_duplicates
            or not df.index.to_series().diff().dropna().eq(pd.Timedelta(hours=1)).all()
        ):
            raise ValueError(f"{name} requires unique consecutive hourly timestamps")
    for col in set(FIELDS[name].split()) - {
        "timestamp",
        "target",
        "strategy",
        "model",
        "topic",
        "sensor_source",
        "controller",
    }:
        df[col] = pd.to_numeric(df[col], errors="raise")
        if not np.isfinite(df[col]).all():
            raise ValueError(f"Invalid value in {name}, field {col}")
    return df


@st.cache_data
def provenance():
    return json.loads((DATA / "10_provenance.json").read_text(encoding="utf8"))


def saved(policy):
    return table("04_dispatch_" + POLICIES[policy])
