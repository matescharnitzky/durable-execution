import json
import os

from langgraph.checkpoint.postgres import PostgresSaver

from langgraph_report.graph import build_graph
from langgraph_report.telemetry import graph_trace
from weather_report.forecast import configure_telemetry
from weather_report.report import arguments, batches, write_report


def main() -> None:
    args = arguments("langgraph")
    configure_telemetry("langgraph")
    database = os.getenv("LANGGRAPH_DATABASE_URL") or "postgresql://weather:weather-local@127.0.0.1:55432/weather"
    with PostgresSaver.from_conn_string(database) as saver:
        saver.setup()
        graph = build_graph(saver)
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
        result = state.values
        if run_input or state.next:
            with graph_trace(args.run_id, args.command) as tracing:
                result = graph.invoke(run_input, config | tracing, durability="sync")
        write_report(args.output, result["results"])
