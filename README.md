# HELIOFLEX — Intelligent Campus Renewable Energy Management

AI-Powered Solar Energy Orchestration & Digital Twin · EcoVibes 2026 research prototype.

## Run locally

From the repository root with Python 3.12:

```sh
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS or Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Use Energy overview to select a date interval, strategy and aggregation. The initial interval matches the dispatch test period. Digital twin simulator accepts scenario inputs and retains the last submitted result. The telemetry page replays saved hourly records. Research impact & report exports the experiment tables and a Markdown report.

## Scientific scope

The 2020 Kitakyushu Science and Research Park profiles contain 8,784 hourly observations. The main dispatch experiment uses the 1,293 held-out hours from November 8 at 03:00 through December 31 at 23:00. Observed PV and load are distinct from scaled PV, battery states, dispatch, illustrative emissions and hypothetical IDR bills. Original archive contents are preserved under `data/helioflex_outputs`. [Dataset](https://doi.org/10.6084/m9.figshare.24978645) · [Paper](https://doi.org/10.1038/s41597-024-04244-6)

The chronological split is 70/15/15 after lag construction. Lowest validation MAE selects lag-24 persistence for solar and histogram gradient boosting for load. The lab displays the original prediction figures and held-out metrics. The separate `data/twin_inputs.csv` contains measured inputs and offline predictions regenerated from the notebook's selected models with scikit-learn 1.6.1. Deployment requires neither training nor a Kaggle connection.

The controller solves a daily linear program against forecasts, then clips planned actions to actual hourly surplus, deficit, power and SOC limits. Rule-based control charges available surplus and discharges during peak tariff hours. At the archived defaults, rule-based control has the lowest simulated bill. Initial stored energy above the default reserve can contribute to apparent savings. End-of-period stored energy receives no financial credit. Neither capital costs nor battery replacement are included in the reported bill.

## Verification

```sh
python -m unittest discover -s tests
```

Regression tests compare every default hourly dispatch field and all strategy summary metrics with their saved CSV values at absolute tolerance 0.00001 in the field's native unit. Additional checks cover non-default energy conservation, SOC recurrence, storage and power limits, observed totals, all six pages, simulation submission and replay controls.

## Publish and deploy

Create an empty GitHub repository named `helioflex` under the deployment account. From this repository run:

```sh
git remote add origin https://github.com/hibscolony/helioflex.git
git push -u origin main
```

In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create app**, select **hibscolony/helioflex**, branch **main**, and main file **streamlit_app.py**. Choose Python 3.12 in advanced settings, then deploy. If using a different GitHub owner, replace the account in the remote and Cloud settings. All data and runtime dependencies travel with the repository. The app needs no broker, credentials, Kaggle runtime or external data download.

