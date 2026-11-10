"""Forecast validation and HTML output for the LangGraph adapter."""

import json
from html import escape
from importlib.resources import files
from pathlib import Path
from tempfile import NamedTemporaryFile

from jsonschema import Draft202012Validator

FIXTURES = files("weather_core").joinpath("fixtures")
VALIDATOR = Draft202012Validator(
    json.loads(FIXTURES.joinpath("report.schema.json").read_text(encoding="utf-8")),
    format_checker=Draft202012Validator.FORMAT_CHECKER,
)


def report_cities(fixture: bool) -> list[str]:
    cities = json.loads(FIXTURES.joinpath("cities.json").read_text(encoding="utf-8"))
    return cities[0][:2] if fixture else [city for batch in cities for city in batch]


def validate_report(result: dict, forecast_date: str, cities: list[str]) -> dict:
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
