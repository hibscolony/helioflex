"""Rebuild selected day-ahead inputs from the supplied research notebook (offline)."""

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

root = Path(__file__).resolve().parent
observed = pd.read_csv(
    root / "data/helioflex_outputs/measured_pv_load_hourly.csv",
    index_col="timestamp",
    parse_dates=True,
)
# Exact calendar and backward-looking feature definitions from the experiment.
# 5. Fitur hari berikutnya, model prediksi, evaluasi dan seleksi validasi
hourly = observed.copy()
hourly["hour"] = hourly.index.hour
hourly["dow"] = hourly.index.dayofweek
hourly["month"] = hourly.index.month
hourly["weekend"] = (hourly["dow"] >= 5).astype(int)
hourly["hour_sin"] = np.sin(2 * np.pi * hourly.hour / 24)
hourly["hour_cos"] = np.cos(2 * np.pi * hourly.hour / 24)
hourly["dow_sin"] = np.sin(2 * np.pi * hourly.dow / 7)
hourly["dow_cos"] = np.cos(2 * np.pi * hourly.dow / 7)
hourly["year_sin"] = np.sin(2 * np.pi * hourly.index.dayofyear / 366)
hourly["year_cos"] = np.cos(2 * np.pi * hourly.index.dayofyear / 366)
for target in ("pv_kw", "load_kw"):
    hourly[f"{target}_lag24"] = hourly[target].shift(24)
    hourly[f"{target}_lag168"] = hourly[target].shift(168)
    hourly[f"{target}_hist7dmean"] = (
        hourly[target].shift(24).rolling(168, min_periods=24).mean()
    )
feat = [
    "hour",
    "dow",
    "month",
    "weekend",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "year_sin",
    "year_cos",
]
feat += [
    f"{t}_{suffix}"
    for t in ("pv_kw", "load_kw")
    for suffix in ("lag24", "lag168", "hist7dmean")
]
feature_df = hourly.dropna(subset=feat + ["pv_kw", "load_kw"]).copy()
if len(feature_df) < 700:
    raise ValueError("Data setelah lag tidak mencukupi")
n = len(feature_df)
a = int(0.70 * n)
b = int(0.85 * n)
train = feature_df.iloc[:a]
valid = feature_df.iloc[a:b]
test = feature_df.iloc[b:]
print("Train:", train.index.min(), train.index.max(), len(train))
print("Valid:", valid.index.min(), valid.index.max(), len(valid))
print("Test :", test.index.min(), test.index.max(), len(test))

model = HistGradientBoostingRegressor(
    max_iter=160,
    max_leaf_nodes=23,
    l2_regularization=2.0,
    learning_rate=0.06,
    random_state=42,
)
history = pd.concat([train, valid])
model.fit(history[feat], history.load_kw)
frame = test[["pv_kw", "load_kw"]].copy()
frame.columns = ["pv_kw_measured", "load_kw_measured"]
frame["pv_kw_forecast"] = test.pv_kw_lag24.clip(lower=0)
frame["load_kw_forecast"] = np.maximum(0, model.predict(test[feat]))
frame.to_csv(root / "data/twin_inputs.csv")
