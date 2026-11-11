"""Shared forecast validation and HTML report exports."""

import json
from datetime import date, datetime, timezone
from html import escape
from importlib.resources import files
from pathlib import Path
from string import Template
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

CORE = files("weather_core")
VALIDATOR = Draft202012Validator(
    json.loads(CORE.joinpath("report_schema.json").read_text(encoding="utf-8")),
    format_checker=Draft202012Validator.FORMAT_CHECKER,
)


def validate_report(result: dict) -> dict:
    VALIDATOR.validate(result)
    if any(row["low_c"] > row["high_c"] for row in result["forecasts"]):
        raise ValueError("Forecast low exceeds its high")
    return result


def write_report(path: Path | None, report: dict, *, experiment: str) -> Path:
    generated = datetime.now(timezone.utc)
    if path is None:
        path = Path("artifacts") / f"report_{experiment.lower()}_{generated:%Y%m%d_%H%M%S_%f}Z.html"
    forecasts = report["forecasts"]
    rows = []
    for row in forecasts:
        city, _, country = row["city"].partition(", ")
        sources = "".join(
            f'<a href="{escape(src["url"])}" title="{escape(src["title"])}">'
            f'{escape(urlsplit(src["url"]).hostname or src["title"])} <span aria-hidden="true">↗</span></a>'
            for src in row["sources"]
        )
        rows.append(
            f'<tr><th scope="row" aria-label="{escape(row["city"])}"><span class="city">{escape(city)}</span>'
            f'<span class="country">{escape(country)}</span></th>'
            f'<td class="temperatures"><span class="low">{row["low_c"]:g}°</span>'
            f'<span class="range-line" aria-hidden="true"></span><strong>{row["high_c"]:g}°</strong></td>'
            f'<td class="conditions">{escape(row["conditions"])}</td>'
            f'<td class="sources">{sources}</td></tr>'
        )
    forecast_date = date.fromisoformat(report["forecast_date"])
    template = Template(CORE.joinpath("report_template.html").read_text(encoding="utf-8"))
    html = template.substitute(
        experiment=escape(experiment),
        forecast_date=forecast_date.isoformat(),
        display_date=forecast_date.strftime("%A, %d %B %Y"),
        summary=escape(report["summary"]),
        city_count=len(forecasts),
        lowest=f'{min(row["low_c"] for row in forecasts):g}',
        highest=f'{max(row["high_c"] for row in forecasts):g}',
        rows="".join(rows),
        generated=generated.strftime("%d %b %Y · %H:%M UTC"),
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
    return path
