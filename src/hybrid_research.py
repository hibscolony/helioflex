"""HELIOFLEX research views: exact archived benchmark and hybrid replay.
No physical device connection. The recorded benchmark is separate from exploratory simulation.
"""
from io import StringIO
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from src.data_loader import table
from src.ui import cards, header, series

START = pd.Timestamp("2020-11-08 03:00:00")
END = pd.Timestamp("2020-12-31 23:00:00")
CAP = 1280.2387663737356
POWER = 288.0537224340905
BENCHMARK = """strategy,grid_import_kwh,curtailed_kwh,PV_utilization_pct,scenario_bill_idr,common_objective_idr,peak_grid_kw,fallback_hours
PV-only,723594,2165,98.10087719298247,1202356800,1202387452.165,1226,0
Rule-based,721640.0875,0,100,1198058192.5,1198377166.375,1226,0
Initial predictive control,723492.783225755,2052.8484495899124,98.19925574597376,1202134123.0966606,1202179710.9322348,1226,0
Initial control · perfect forecast,721640.0875,0,100,1198058192.5,1198377166.375,1226,0
MPC,721975.348562554,371.4804017218893,99.67413999848958,1198821790.8249288,1199091293.16891,1226,0
HELIOFLEX,721640.0875,0,100,1198058192.5,1198377166.375,1226,151
Oracle · cost,721640.0875,0,100,1198058192.5,1198377166.375,1226,0
Oracle · grid,721640.0875,0,100,1199425931.25,1199744905.125,1226,0
Oracle · equal terminal SOC,721640.0875,0,100,1198058192.5,1198377166.375,1226,0
"""
SENSITIVITY = """scale,capacity,power,strategy,grid_import_kwh,curtailed_kwh
1,640.1193831868678,144.02686121704525,Rule-based,833149,0
1,640.1193831868678,144.02686121704525,HELIOFLEX,833149,0
1,1280.2387663737356,288.0537224340905,Rule-based,833149,0
1,1280.2387663737356,288.0537224340905,HELIOFLEX,833149,0
25,640.1193831868678,144.02686121704525,Rule-based,778429,0
25,640.1193831868678,144.02686121704525,HELIOFLEX,778429,0
25,1280.2387663737356,288.0537224340905,Rule-based,778429,0
25,1280.2387663737356,288.0537224340905,HELIOFLEX,778429,0
50,640.1193831868678,144.02686121704525,Rule-based,721709.4830310065,76.892555131819
50,640.1193831868678,144.02686121704525,HELIOFLEX,721709.4830310065,76.892555131819
50,1280.2387663737356,288.0537224340905,Rule-based,721640.0875,0
50,1280.2387663737356,288.0537224340905,HELIOFLEX,721640.0875,0
"""
# Exact discharge differences and decision ranges extracted from dispatch_hybrid.csv
# relative to the bundled rule-based hourly record. SOC is reconstructed, not interpolated.
DISCHARGE = {14:0.,158:0.,302:158.83999999999995,326:0.,350:286.09250000000003,494:0.,518:0.,520:164.25499999999997,662:0.,686:0.,998:0.,1022:0.,1046:288.0537224340905,1047:288.0537224340905,1048:69.18005513181885,1166:0.,1238:151.61999999999995}
SURPLUS = [(6,10),(153,153),(318,321),(367,368),(488,488),(512,512),(514,514),(654,656),(681,682),(993,994),(1015,1015),(1018,1018),(1161,1161),(1231,1231),(1233,1233),(1258,1258),(1281,1282)]
FALLBACK = [(24,30),(346,366),(371,395),(541,559),(657,658),(1044,1064),(1234,1257),(1259,1280),(1283,1292)]
LOW = [(24,30),(346,367),(371,395),(541,559),(657,658),(1044,1064),(1233,1292)]

def benchmark():
    return pd.read_csv(StringIO(BENCHMARK))

def sensitivity_data():
    return pd.read_csv(StringIO(SENSITIVITY))

@st.cache_data(show_spinner=False)
def hybrid_record():
    f = table("04_dispatch_Rule_based").copy()
    if len(f) != 1293 or f.index[0] != START or f.index[-1] != END:
        raise ValueError("Archived reference timestamps do not match research period.")
    if not np.allclose([f.load_kwh.sum(), f.pv_kwh.sum(), f.charge_kwh.sum(), f.grid_import_kwh.sum()], [835429,114000,2165,721640.0875], rtol=0, atol=1e-6):
        raise ValueError("Archived reference values do not match the research archive.")
    for i,v in DISCHARGE.items():
        f.iloc[i, f.columns.get_loc("discharge_kwh")] = v
    f["grid_import_kwh"] = (f.load_kwh-f.pv_kwh).clip(lower=0)-f.discharge_kwh
    f["curtailment_kwh"] = (f.pv_kwh-f.load_kwh).clip(lower=0)-f.charge_kwh
    f["soc_kwh"] = 0.1*CAP + (0.95*f.charge_kwh-f.discharge_kwh/0.95).cumsum()
    f["bill_idr"] = f.grid_import_kwh*f.tariff_idr_per_kwh
    f["decision"]="mpc"
    f["low_confidence"]=False
    for ranges,label in [(SURPLUS,"surplus-capture"),(FALLBACK,"confidence-fallback")]:
        for i,j in ranges: f.iloc[i:j+1,f.columns.get_loc("decision")]=label
    for i,j in LOW: f.iloc[i:j+1,f.columns.get_loc("low_confidence")]=True
    residual=f.pv_kwh+f.grid_import_kwh+f.discharge_kwh-f.load_kwh-f.charge_kwh-f.curtailment_kwh
    if (residual.abs().max()>1e-6 or f.soc_kwh.min()<0.1*CAP-1e-6 or f.soc_kwh.max()>0.9*CAP+1e-6
        or f.charge_kwh.max()>POWER+1e-6 or f.discharge_kwh.max()>POWER+1e-6
        or not np.allclose([f.grid_import_kwh.sum(),f.curtailment_kwh.sum(),f.bill_idr.sum(),f.soc_kwh.iloc[-1]],[721640.0875,0,1198058192.5,0.1*CAP],rtol=0,atol=1e-5)):
        raise ValueError("Research replay failed energy or benchmark audit.")
    return f

def scope():
    st.caption("Recorded experiment · 8 Nov 2020 03:00 – 31 Dec 2020 23:00 · 1,293 hours · Kitakyushu")
    st.caption("Measured load and original PV; expanded PV, battery, tariff and dispatch are simulated. No hardware connection.")

def overview():
    header("Energy overview","Energy command center","Hybrid predictive control · campus solar and battery")
    scope()
    f=hybrid_record()
    b=benchmark().set_index("strategy")
    h=b.loc["HELIOFLEX"]
    cards([("Campus load","835,429 kWh","Exact test window · measured"),
           ("Scenario PV","114,000 kWh","50× measured PV"),
           ("Grid import",f"{h.grid_import_kwh:,.2f} kWh","Simulated"),
           ("Solar utilization","100.00%","Includes charging; not conversion efficiency"),
           ("Curtailment","0 kWh","Simulated"),
           ("Scenario bill",f"IDR {h.scenario_bill_idr:,.0f}","Illustrative tariff")])
    st.info("HELIOFLEX matches rule-based and the cost oracle at the main configuration; superiority over rule-based is not established.")
    st.subheader("Energy flow")
    period=st.radio("Aggregate by",["Daily","Weekly"],horizontal=True)
    series(f[["pv_kwh","load_kwh","grid_import_kwh"]].resample({"Daily":"D","Weekly":"W"}[period]).sum().rename(columns={"pv_kwh":"Scenario PV","load_kwh":"Measured load","grid_import_kwh":"Grid import"}),"kWh")
    series(f[["soc_kwh"]].rename(columns={"soc_kwh":"Stored energy"}),"kWh")
    st.download_button("Download hourly HELIOFLEX replay",f.to_csv(),"helioflex_dispatch.csv","text/csv")

def comparison():
    header("Experimental results","Strategy comparison","Shared inputs, storage parameters and illustrative tariff")
    scope()
    df=benchmark()
    metric=st.selectbox("Metric",["curtailed_kwh","grid_import_kwh","scenario_bill_idr","common_objective_idr","PV_utilization_pct","peak_grid_kw"])
    fig=px.bar(df,x="strategy",y=metric,color="strategy",color_discrete_map={"HELIOFLEX":"#17634a"})
    fig.update_layout(showlegend=False,xaxis_title=None)
    st.plotly_chart(fig,width="stretch")
    st.dataframe(df,hide_index=True,width="stretch")
    cards([("Import reduction vs initial control","1,852.70 kWh","Diagnostic comparison"),("Curtailment reduction","100%","2,052.85 → 0 kWh"),("Bill reduction vs initial control","IDR 4,075,931","Excludes investment")])
    st.write("The oracle uses future actual values only as a retrospective bound. The hybrid controller was developed after the initial test results were observed, so this is a diagnostic comparison, not independent validation.")
    st.download_button("Download benchmark CSV",df.to_csv(index=False),"helioflex_benchmark.csv","text/csv")

def sensitivity():
    header("Digital twin simulator","Recorded scenario explorer","Choose among the six evaluated PV and battery configurations")
    scope()
    df=sensitivity_data()
    scale=st.select_slider("PV expansion multiplier",options=[1,25,50],value=50)
    cap=st.radio("Battery capacity",[640.1193831868678,CAP],index=1,format_func=lambda v:f"{v:,.2f} kWh",horizontal=True)
    selected=df[(df.scale==scale)&np.isclose(df.capacity,cap)]
    st.dataframe(selected,hide_index=True,width="stretch")
    st.caption("Recorded scenarios only; battery power scales with capacity. A separate fixed-power audit at 288.05 kW gave 721,640.09 kWh import for both battery capacities, for both HELIOFLEX and rule-based at 50× PV.")
    st.subheader("Sensitivity across configurations")
    st.plotly_chart(px.line(df,x="scale",y="grid_import_kwh",color="strategy",line_dash="capacity",markers=True),width="stretch")
    st.write("40% target PV share was not reached: 17.73% on the annual profile and 13.65% during the test window.")
    st.download_button("Download sensitivity CSV",df.to_csv(index=False),"helioflex_sensitivity.csv","text/csv")

def telemetry():
    header("Virtual IoT monitoring","Historical telemetry","Recorded hybrid controller · virtual data replay")
    scope()
    f=hybrid_record()
    i=st.slider("Hour in recorded experiment",0,len(f)-1,0)
    r=f.iloc[i]
    st.subheader(str(f.index[i]))
    cards([("PV scenario",f"{r.pv_kwh:,.1f} kW","Simulated"),("Campus load",f"{r.load_kwh:,.1f} kW","Measured"),("Grid import",f"{r.grid_import_kwh:,.1f} kW","Simulated"),("Battery SOC",f"{100*r.soc_kwh/CAP:.1f}%","Simulated")])
    st.info("Controller decision: "+r.decision)
    st.dataframe(f.iloc[max(0,i-47):i+1].tail(12),width="stretch")
    series(f.iloc[max(0,i-47):i+1][["pv_kwh","load_kwh","grid_import_kwh"]],"kW")
    st.caption("1,112 MPC hours · 151 confidence-fallback hours · 30 surplus-capture hours")

def report():
    header("Research impact & report","Experiment record","Reproducible archived results and simulation integrity")
    scope()
    f=hybrid_record()
    residual=f.pv_kwh+f.grid_import_kwh+f.discharge_kwh-f.load_kwh-f.charge_kwh-f.curtailment_kwh
    st.write("Hourly energy balance maximum residual:",float(residual.abs().max()),"kWh")
    st.write("SOC range:",float(f.soc_kwh.min()/CAP*100), "to",float(f.soc_kwh.max()/CAP*100),"%")
    st.write("Original experiment: maximum SOC recurrence residual 4.26e-14 kWh; zero solver failures.")
    st.write("Model selection: persistence for PV, HistGradientBoost for load; rolling horizon 24 hours; fallback threshold twice validation MAE; 95% charge/discharge efficiencies.")
    st.write("The dataset is from Japan. Campus Indonesia feasibility, physical sensing, independent validation, actual tariffs and capital costs are not established.")
    st.markdown("[Dataset](https://doi.org/10.6084/m9.figshare.24978645) · [Scientific Data paper](https://doi.org/10.1038/s41597-024-04244-6)")
    st.download_button("Download recorded benchmark",benchmark().to_csv(index=False),"helioflex_benchmark.csv","text/csv")
    st.download_button("Download hourly replay",f.to_csv(),"helioflex_dispatch.csv","text/csv")
