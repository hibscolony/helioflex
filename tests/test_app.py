import unittest
import numpy as np
from streamlit.testing.v1 import AppTest
from src.data_loader import ROOT, DATA, table, saved, provenance, POLICIES
from src.digital_twin import dispatch, summarize


class ExperimentTests(unittest.TestCase):
    def test_hourly_reference(self):
        inputs = table("twin_inputs")
        measured = table("measured_pv_load_hourly")
        np.testing.assert_allclose(inputs.iloc[:, :2], measured.loc[inputs.index])
        quality = table("data_quality_summary").set_index("Unnamed: 0").value
        self.assertEqual(len(measured), quality.observed_hours)
        np.testing.assert_allclose(
            measured.sum(),
            [quality.pv_measured_kwh, quality.electricity_load_measured_kwh],
        )
        p = provenance()
        reference = table("05_strategy_comparison").set_index("strategy")
        for policy in POLICIES:
            cap = reference.at[policy, "battery_kwh"]
            df = dispatch(inputs, policy, 50, cap, p["battery_kw_assumed"])
            np.testing.assert_array_equal(df.index, saved(policy).index)
            np.testing.assert_allclose(df, saved(policy), rtol=0, atol=1e-5)
            totals = summarize(df, policy, 50, cap)
            for field, value in reference.loc[policy].items():
                self.assertAlmostEqual(value, totals[field], delta=1e-5)

    def test_custom_constraints(self):
        for policy in ["Rule-based", "HELIOFLEX"]:
            out = dispatch(
                table("twin_inputs").iloc[:96], policy, 100, 500, 15, 0.55, 5000, 400
            )
            np.testing.assert_allclose(
                out.pv_kwh + out.grid_import_kwh + out.discharge_kwh,
                out.load_kwh + out.charge_kwh + out.curtailment_kwh,
            )
            np.testing.assert_allclose(
                np.diff(np.r_[275, out.soc_kwh]),
                out.charge_kwh * 0.95 - out.discharge_kwh / 0.95,
                atol=1e-8,
            )
            self.assertTrue(out.soc_kwh.between(50, 450).all())
            self.assertTrue(
                out.charge_kwh.between(0, 15).all()
                and out.discharge_kwh.between(0, 15).all()
            )

    def test_pages(self):
        app = AppTest.from_file(
            str(ROOT / "streamlit_app.py"), default_timeout=40
        ).run()
        for page in app.sidebar.radio[0].options:
            app.sidebar.radio[0].set_value(page).run()
            self.assertFalse(list(app.exception) + list(app.error), page)
            if page == "Digital twin simulator":
                app.button[0].click().run()
                self.assertIn("scenario", app.session_state)
            if page == "Virtual IoT monitoring":
                app.button[0].click().run()
                self.assertGreater(app.session_state["cursor"], 0)
                app.button[1].click().run()
                self.assertFalse(app.session_state["playing"])
                app.button[2].click().run()
                self.assertEqual(app.session_state["cursor"], 0)
            self.assertFalse(list(app.exception) + list(app.error), page)
