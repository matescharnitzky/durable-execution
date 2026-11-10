"""Shared input, validation, and HTML output for the Python adapters."""

import argparse
import json
from datetime import date
from html import escape
from importlib.resources import files
from pathlib import Path
from tempfile import NamedTemporaryFile

from jsonschema import Draft202012Validator

FIXTURES = files("weather_report").joinpath("fixtures")
VALIDATOR = Draft202012Validator(
    json.loads(FIXTURES.joinpath("report.schema.json").read_text(encoding="utf-8")),
    format_checker=Draft202012Validator.FORMAT_CHECKER,
)


def arguments(runtime: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=f"{runtime}-report")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "status", "resume"):
        command = commands.add_parser(name)
        command.add_argument("run_id")
        if name != "status":
            command.add_argument("--output", type=Path, required=True)
        if name == "run":
            command.add_argument("--date", type=date.fromisoformat, required=True)
            command.add_argument("--fixture", action="store_true", help="Use two one-city batches")
    return parser.parse_args()


def batches(fixture: bool) -> list[list[str]]:
    cities = json.loads(FIXTURES.joinpath("cities.json").read_text(encoding="utf-8"))
    return [[city] for city in cities[0][:2]] if fixture else cities


def validate_batch(result: dict, forecast_date: str, cities: list[str]) -> dict:
    VALIDATOR.validate(result)
    if result["forecast_date"] != forecast_date:
        raise ValueError("Forecast date does not match the request")
    if [row["city"] for row in result["forecasts"]] != cities:
        raise ValueError("Forecast cities do not match the requested order")
    if any(row["low_c"] > row["high_c"] for row in result["forecasts"]):
        raise ValueError("Forecast low exceeds its high")
    return result


def write_report(path: Path, results: list[dict]) -> None:
    forecast_date = escape(results[0]["forecast_date"])
    summaries = "\n".join(f"<p>{escape(batch['summary'])}</p>" for batch in results)
    rows = []
    for result in results:
        for row in result["forecasts"]:
            sources = ", ".join(
                f'<a href="{escape(src["url"])}">{escape(src["title"])}</a>'
                for src in row["sources"]
            )
            rows.append(
                f"<tr><th scope=\"row\">{escape(row['city'])}</th>"
                f"<td>{row['low_c']}–{row['high_c']} °C</td>"
                f"<td>{escape(row['conditions'])}</td><td>{sources}</td></tr>"
            )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        f"<title>Weather forecast for {forecast_date}</title>"
        f"<h1>Weather forecast for {forecast_date}</h1>{summaries}"
        '<table><thead><tr><th>City</th><th>Low–high</th><th>Conditions</th><th>Sources</th></tr>'
        f"</thead><tbody>{''.join(rows)}</tbody></table></html>\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(html)
            output.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
