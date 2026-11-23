"""Hourly solar-only storage model ported from the HELIOFLEX experiment."""

import warnings
import numpy as np
import pandas as pd
from scipy.optimize import linprog

PEAK_HOURS = (17, 18, 19, 20, 21)
ETA_CHARGE = ETA_DISCHARGE = 0.95
SOC_MIN_FRAC, SOC_MAX_FRAC = 0.1, 0.9
DEGRADATION_COST_IDR_PER_KWH = 70.0
CO2_KG_PER_KWH_ASSUMPTION = 0.70


def tariffs_for(index, peak, offpeak):
    return np.where(
        pd.DatetimeIndex(index).hour.isin(PEAK_HOURS), peak, offpeak
    ).astype(float)


def day_ahead_plan(pred_pv, pred_load, price, initial_soc, capacity, max_power):
    """LP: solar-only battery; prediction only, not future actual values.
    x=[charge(H), discharge(H), grid(H), curtail(H), soc(H+1), peak(1)].
    """
    H = len(pred_pv)
    pv = np.maximum(0, np.asarray(pred_pv, float))
    load = np.maximum(0, np.asarray(pred_load, float))
    if capacity <= 0 or max_power <= 0:
        return np.zeros(H), np.zeros(H)
    nvar = 5 * H + 2
    C = np.arange(0, H)
    D = np.arange(H, 2 * H)
    G = np.arange(2 * H, 3 * H)
    W = np.arange(3 * H, 4 * H)
    S = np.arange(4 * H, 5 * H + 1)
    PK = nvar - 1
    obj = np.zeros(nvar)
    obj[G] = price
    obj[C] = DEGRADATION_COST_IDR_PER_KWH
    obj[D] = DEGRADATION_COST_IDR_PER_KWH
    obj[W] = 0.001
    obj[PK] = 25.0  # penalti peak sebagai objektif sekunder
    Aeq = []
    beq = []
    for h in range(H):
        balance = np.zeros(nvar)
        balance[G[h]] = 1
        balance[D[h]] = 1
        balance[C[h]] = -1
        balance[W[h]] = -1
        Aeq.append(balance)
        beq.append(load[h] - pv[h])
        socrow = np.zeros(nvar)
        socrow[S[h + 1]] = 1
        socrow[S[h]] = -1
        socrow[C[h]] = -ETA_CHARGE
        socrow[D[h]] = 1 / ETA_DISCHARGE
        Aeq.append(socrow)
        beq.append(0)
    initial = np.zeros(nvar)
    initial[S[0]] = 1
    Aeq.append(initial)
    beq.append(initial_soc)
    Aub = []
    bub = []
    for h in range(H):
        row = np.zeros(nvar)
        row[G[h]] = 1
        row[PK] = -1
        Aub.append(row)
        bub.append(0)
    min_soc, max_soc = SOC_MIN_FRAC * capacity, SOC_MAX_FRAC * capacity
    bounds = [(0, min(max_power, max(0, pv[h] - load[h]))) for h in range(H)]
    bounds += [(0, min(max_power, max(0, load[h] - pv[h]))) for h in range(H)]
    bounds += (
        [(0, None)] * H + [(0, None)] * H + [(min_soc, max_soc)] * (H + 1) + [(0, None)]
    )
    sol = linprog(
        obj,
        A_ub=np.array(Aub),
        b_ub=np.array(bub),
        A_eq=np.array(Aeq),
        b_eq=np.array(beq),
        bounds=bounds,
        method="highs",
    )
    if not sol.success:
        warnings.warn(
            "LP tidak feasible, tindakan baterai nol untuk hari tersebut: "
            + sol.message
        )
        return np.zeros(H), np.zeros(H)
    return sol.x[C], sol.x[D]


def dispatch(
    df,
    mode,
    pv_scale,
    battery_kwh,
    battery_kw,
    initial_fraction=0.10,
    peak=2200.0,
    offpeak=1500.0,
):
    frame = df.copy().sort_index()
    pv = frame["pv_kw_measured"].to_numpy(dtype=float) * pv_scale
    load = frame["load_kw_measured"].to_numpy(dtype=float)
    pr_pv = frame["pv_kw_forecast"].to_numpy(dtype=float) * pv_scale
    pr_load = frame["load_kw_forecast"].to_numpy(dtype=float)
    prices = tariffs_for(frame.index, peak, offpeak)
    n = len(frame)
    soc_min = SOC_MIN_FRAC * battery_kwh
    soc_max = SOC_MAX_FRAC * battery_kwh
    soc = battery_kwh * initial_fraction
    rec = []
    day = frame.index.normalize()
    for date in pd.Index(day).unique():
        inds = np.where(day == date)[0]
        if mode == "HELIOFLEX" and battery_kwh > 0:
            target_c, target_d = day_ahead_plan(
                pr_pv[inds], pr_load[inds], prices[inds], soc, battery_kwh, battery_kw
            )
        else:
            target_c = np.zeros(len(inds))
            target_d = np.zeros(len(inds))
        for local_idx, i in enumerate(inds):
            surplus = max(0, pv[i] - load[i])
            deficit = max(0, load[i] - pv[i])
            charge = 0.0
            discharge = 0.0
            if mode == "Rule-based" and battery_kwh > 0:
                charge = min(surplus, battery_kw, (soc_max - soc) / ETA_CHARGE)
                if frame.index[i].hour in PEAK_HOURS:
                    discharge = min(
                        deficit, battery_kw, (soc - soc_min) * ETA_DISCHARGE
                    )
            elif mode == "HELIOFLEX" and battery_kwh > 0:
                charge = min(
                    target_c[local_idx],
                    surplus,
                    battery_kw,
                    max(0, (soc_max - soc) / ETA_CHARGE),
                )
                discharge = min(
                    target_d[local_idx],
                    deficit,
                    battery_kw,
                    max(0, (soc - soc_min) * ETA_DISCHARGE),
                )
            soc = (
                float(
                    np.clip(
                        soc + charge * ETA_CHARGE - discharge / ETA_DISCHARGE,
                        soc_min,
                        soc_max,
                    )
                )
                if battery_kwh > 0
                else 0.0
            )
            grid = deficit - discharge
            curtailed = surplus - charge
            # Energy balance: PV+import+discharge=load+charge+curtail (1-hour time steps)
            assert (
                abs((pv[i] + grid + discharge) - (load[i] + charge + curtailed)) < 1e-5
            )
            rec.append(
                (
                    frame.index[i],
                    pv[i],
                    load[i],
                    grid,
                    curtailed,
                    charge,
                    discharge,
                    soc,
                    prices[i],
                    grid * prices[i],
                )
            )
    fields = [
        "timestamp",
        "pv_kwh",
        "load_kwh",
        "grid_import_kwh",
        "curtailment_kwh",
        "charge_kwh",
        "discharge_kwh",
        "soc_kwh",
        "tariff_idr_per_kwh",
        "bill_idr",
    ]
    return pd.DataFrame(rec, columns=fields).set_index("timestamp")


def summarize(output, policy, scale, capacity):
    load = output.load_kwh.sum()
    generation = output.pv_kwh.sum()
    imp = output.grid_import_kwh.sum()
    return {
        "strategy": policy,
        "pv_scale": scale,
        "battery_kwh": capacity,
        "observed_load_kwh": load,
        "scenario_pv_generation_kwh": generation,
        "grid_import_kwh": imp,
        "peak_grid_kw": output.grid_import_kwh.max(),
        "curtailed_kwh": output.curtailment_kwh.sum(),
        "PV_utilization_pct": 100
        * (1 - output.curtailment_kwh.sum() / max(generation, 1e-9)),
        "grid_displacement_pct": 100 * (1 - imp / max(load, 1e-9)),
        "scenario_bill_idr": output.bill_idr.sum(),
        "illustrative_grid_co2_kg": imp * CO2_KG_PER_KWH_ASSUMPTION,
    }
