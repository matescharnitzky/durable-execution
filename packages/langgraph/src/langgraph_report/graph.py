from typing import TypedDict

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from openai import APIConnectionError, InternalServerError, RateLimitError

from langgraph_report.search import search_forecast


class ReportState(TypedDict):
    run_id: str
    forecast_date: str
    batches: list[list[str]]
    results: list[dict]


def forecast(state: ReportState) -> dict:
    index = len(state["results"])
    result = search_forecast.invoke({
        "forecast_date": state["forecast_date"],
        "cities": state["batches"][index],
    }, config={"metadata": {"durable.batch": index + 1}})
    return {"results": [*state["results"], result]}


def next_node(state: ReportState) -> str:
    return END if len(state["results"]) == len(state["batches"]) else "forecast"


def build_graph(checkpointer: PostgresSaver):
    builder = StateGraph(ReportState)
    builder.add_node("forecast", forecast, retry_policy=RetryPolicy(
        initial_interval=1, max_attempts=3, retry_on=(APIConnectionError, InternalServerError, RateLimitError),
    ))
    builder.add_edge(START, "forecast")
    builder.add_conditional_edges("forecast", next_node, ["forecast", END])
    return builder.compile(checkpointer=checkpointer, name="Weather report")
