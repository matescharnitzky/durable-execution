import json
import os
from typing import TypedDict

import logfire
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from weather_report.forecast import RetryableForecastError, configure_telemetry, search_forecast
from weather_report.report import arguments, batches, write_report


class ReportState(TypedDict):
    run_id: str
    forecast_date: str
    batches: list[list[str]]
    results: list[dict]


def forecast(state: ReportState) -> dict:
    index = len(state["results"])
    result = search_forecast(
        "langgraph", state["run_id"], index + 1, state["forecast_date"], state["batches"][index]
    )
    return {"results": [*state["results"], result]}


def next_node(state: ReportState) -> str:
    return END if len(state["results"]) == len(state["batches"]) else "forecast"


def main() -> None:
    args = arguments("langgraph")
    configure_telemetry("langgraph")
    database = os.getenv("LANGGRAPH_DATABASE_URL") or "postgresql://weather:weather-local@127.0.0.1:55432/weather"
    with PostgresSaver.from_conn_string(database) as saver:
        saver.setup()
        builder = StateGraph(ReportState)
        builder.add_node("forecast", forecast, retry_policy=RetryPolicy(
            initial_interval=1, max_attempts=3, retry_on=RetryableForecastError,
        ))
        builder.add_edge(START, "forecast")
        builder.add_conditional_edges("forecast", next_node, ["forecast", END])
        graph = builder.compile(checkpointer=saver)
        config = {"configurable": {"thread_id": args.run_id}}
        state = graph.get_state(config)
        if args.command == "status":
            print(json.dumps({
                "run_id": args.run_id,
                "state": ("pending" if state.next else "complete") if state.values else "unknown",
                "completed_batches": len(state.values.get("results", [])),
                "next": list(state.next),
            }))
            return
        if args.command == "run":
            if state.values:
                raise SystemExit("Run ID already exists. Use resume.")
            run_input = {
                "run_id": args.run_id,
                "forecast_date": args.date.isoformat(),
                "batches": batches(args.fixture),
                "results": [],
            }
        else:
            if not state.values:
                raise SystemExit("Unknown run ID.")
            run_input = None
        with logfire.span(
            "LangGraph {command}", command=args.command,
            **{"durable.runtime": "langgraph", "durable.run_id": args.run_id},
        ):
            result = graph.invoke(run_input, config, durability="sync") if run_input or state.next else state.values
        write_report(args.output, result["results"])
