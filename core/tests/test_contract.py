import json
import unittest
from importlib.resources import files

from jsonschema import Draft202012Validator

FIXTURES = files("weather_core").joinpath("fixtures")


class ReportContractTest(unittest.TestCase):
    def test_live_workload_has_four_batches_of_five_distinct_cities(self):
        batches = json.loads(FIXTURES.joinpath("cities.json").read_text(encoding="utf-8"))

        self.assertEqual([len(batch) for batch in batches], [5, 5, 5, 5])
        self.assertEqual(len({city for batch in batches for city in batch}), 20)

    def test_sample_report_matches_contract(self):
        schema = json.loads(FIXTURES.joinpath("report.schema.json").read_text(encoding="utf-8"))
        report = json.loads(FIXTURES.joinpath("report.json").read_text(encoding="utf-8"))

        Draft202012Validator.check_schema(schema)
        Draft202012Validator(
            schema, format_checker=Draft202012Validator.FORMAT_CHECKER
        ).validate(report)
        for forecast in report["forecasts"]:
            self.assertLessEqual(forecast["low_c"], forecast["high_c"])
