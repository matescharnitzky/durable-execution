import json
import unittest
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator

CORE = files("weather_core")
TESTS = Path(__file__).parent


class ReportContractTest(unittest.TestCase):
    def test_sample_report_matches_contract(self):
        schema = json.loads(CORE.joinpath("report_schema.json").read_text(encoding="utf-8"))
        report = json.loads(TESTS.joinpath("report.json").read_text(encoding="utf-8"))

        Draft202012Validator.check_schema(schema)
        Draft202012Validator(
            schema, format_checker=Draft202012Validator.FORMAT_CHECKER
        ).validate(report)
        for forecast in report["forecasts"]:
            self.assertLessEqual(forecast["low_c"], forecast["high_c"])
