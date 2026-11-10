"""OpenAI-hosted forecast searches with retries delegated to the runtime."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import logfire

from weather_report.report import validate_batch


class RetryableForecastError(Exception):
    """Transient failure before the worker could consume the OpenAI response."""


def configure_telemetry(runtime: str) -> None:
    logfire.configure(
        service_name=f"{runtime}-report",
        send_to_logfire="if-token-present",
        console=False,
    )


def search_forecast(runtime: str, run_id: str, batch: int, forecast_date: str, cities: list[str]) -> dict:
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        "tools": [{"type": "web_search"}],
        "tool_choice": "required",
        "instructions": (
            "Find forecasts for the requested local calendar date and cities. "
            "Return only a JSON object with forecast_date, summary, and forecasts. "
            "Each forecast must include city, low_c, high_c, conditions, and sources "
            "(objects with title and URL in the url field). Use exact input city names "
            "in order, Celsius, and real forecast sources. Never invent data."
        ),
        "input": json.dumps({"forecast_date": forecast_date, "cities": cities}),
    }
    request = Request(
        f"{base_url}/responses",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with logfire.span(
        "OpenAI forecast search",
        **{"durable.runtime": runtime, "durable.run_id": run_id, "durable.batch": batch},
    ):
        try:
            with urlopen(request, timeout=90) as response:
                output = json.load(response)["output"]
        except HTTPError as error:
            status = error.code
            error.close()
            if status in (408, 429) or status >= 500:
                raise RetryableForecastError(f"OpenAI HTTP {status}") from None
            raise RuntimeError(f"OpenAI HTTP {status}") from None
        except (URLError, TimeoutError, ConnectionError) as error:
            raise RetryableForecastError(type(error).__name__) from None
        text = "".join(
            content["text"]
            for item in output
            if item["type"] == "message"
            for content in item["content"]
            if content["type"] == "output_text"
        ).strip()
        if text.startswith("```json\n") and text.endswith("\n```"):
            text = text[8:-4]
        return validate_batch(json.loads(text), forecast_date, cities)
