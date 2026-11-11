import json
import os
import tempfile
import unittest
from pathlib import Path

from weather_core.report import validate_report, write_report

SAMPLE = Path(__file__).with_name("report.json")


class ReportOutputTest(unittest.TestCase):
    def test_unknown_forecasts_do_not_become_zero_temperatures(self):
        report = json.loads(SAMPLE.read_text())
        for row in report["forecasts"]:
            row.update(low_c=None, high_c=None, conditions="Forecast unavailable", sources=[])
        validate_report(report)
        with tempfile.TemporaryDirectory() as directory:
            html = write_report(Path(directory) / "report.html", report, experiment="DBOS").read_text()
        self.assertIn('class="unavailable">Unavailable', html)
        self.assertIn("No verified source", html)
        self.assertIn("<dd>—</dd>", html)
        self.assertNotIn("0°", html)

    def test_real_zero_is_preserved_and_missing_values_do_not_affect_extremes(self):
        report = json.loads(SAMPLE.read_text())
        report["forecasts"][0].update(low_c=0, high_c=0)
        report["forecasts"][1].update(low_c=None, high_c=None)
        validate_report(report)
        with tempfile.TemporaryDirectory() as directory:
            html = write_report(Path(directory) / "report.html", report, experiment="DBOS").read_text()
        self.assertIn("<strong>0°</strong>", html)
        self.assertEqual(html.count("<dd>0°</dd>"), 2)

    def test_default_exports_have_distinct_timestamped_names(self):
        report = json.loads(SAMPLE.read_text())
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                first = write_report(None, report, experiment="LangGraph")
                second = write_report(None, report, experiment="LangGraph")
                self.assertRegex(first.name, r"^report_langgraph_\d{8}_\d{6}_\d{6}Z\.html$")
                self.assertEqual(first.parent, Path("artifacts/langgraph"))
                self.assertNotEqual(first, second)
                self.assertTrue(first.is_file() and second.is_file())
            finally:
                os.chdir(previous)

    def test_custom_path_preserves_sources_and_escapes_model_text(self):
        report = json.loads(SAMPLE.read_text())
        report["summary"] = '<script>alert("summary")</script>'
        report["forecasts"][0]["city"] = "<b>Budapest</b>, Hungary"
        report["forecasts"][0]["conditions"] = "Rain & snow"
        report["forecasts"][0]["sources"][0]["title"] = 'Forecast" onmouseover="alert(1)'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested/custom.html"
            self.assertEqual(write_report(output, report, experiment="LangGraph"), output)
            html = output.read_text()
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>Budapest</b>", html)
        self.assertIn("&lt;b&gt;Budapest&lt;/b&gt;", html)
        self.assertIn("Rain &amp; snow", html)
        self.assertIn("Forecast&quot; onmouseover=&quot;alert(1)", html)
        for forecast in report["forecasts"]:
            for source in forecast["sources"]:
                self.assertIn(source["url"], html)

    def test_shared_exports_use_each_experiment_name(self):
        report = json.loads(SAMPLE.read_text())
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                for experiment in ("LangGraph", "DBOS", "Temporal", "Pi"):
                    with self.subTest(experiment=experiment):
                        path = write_report(None, report, experiment=experiment)
                        self.assertTrue(path.name.startswith(f"report_{experiment.lower()}_"))
                        self.assertEqual(path.parent, Path("artifacts") / experiment.lower())
                        self.assertIn(f'<span class="experiment">{experiment}</span>', path.read_text())
                        self.assertIn(f'{experiment} · Weather forecast', path.read_text())
            finally:
                os.chdir(previous)
