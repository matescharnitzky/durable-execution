import json
import os
import tempfile
import unittest
from pathlib import Path

from langgraph_report.report import write_report

SAMPLE = Path(__file__).resolve().parents[3] / "core/tests/report.json"


class ReportOutputTest(unittest.TestCase):
    def test_default_exports_have_distinct_timestamped_names(self):
        report = json.loads(SAMPLE.read_text())
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                first = write_report(None, report)
                second = write_report(None, report)
                self.assertRegex(first.name, r"^report_langgraph_\d{8}_\d{6}_\d{6}Z\.html$")
                self.assertEqual(first.parent, Path("artifacts"))
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
            self.assertEqual(write_report(output, report), output)
            html = output.read_text()
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>Budapest</b>", html)
        self.assertIn("&lt;b&gt;Budapest&lt;/b&gt;", html)
        self.assertIn("Rain &amp; snow", html)
        self.assertIn("Forecast&quot; onmouseover=&quot;alert(1)", html)
        for forecast in report["forecasts"]:
            for source in forecast["sources"]:
                self.assertIn(source["url"], html)
