import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph_report.report import FIXTURES, validate_batch

SEARCH = json.loads(FIXTURES.joinpath("search.json").read_text(encoding="utf-8"))


@tool
def search_forecast(forecast_date: str, cities: list[str]) -> dict:
    """Find cited weather forecasts for a batch using OpenAI web search."""
    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL") or SEARCH["model"],
        use_responses_api=True,
        max_retries=0,
        timeout=90,
    ).bind_tools([{"type": "web_search"}], tool_choice="required")
    response = model.invoke([
        SystemMessage(SEARCH["instructions"]),
        HumanMessage(json.dumps({"forecast_date": forecast_date, "cities": cities})),
    ])
    text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
    return validate_batch(json.loads(text), forecast_date, cities)
