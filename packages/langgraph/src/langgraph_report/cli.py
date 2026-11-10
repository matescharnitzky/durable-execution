import json
import os

from langgraph_report.report import arguments, batches, write_report


def main() -> None:
    args = arguments("langgraph")

    # Logfire's LangGraph integration reads these before framework imports.
    os.environ.pop("LANGSMITH_TRACING_MODE", None)
    os.environ.update(
        LANGSMITH_TRACING="true",
        LANGSMITH_OTEL_ENABLED="true",
        LANGSMITH_OTEL_ONLY="true",
        LANGSMITH_HIDE_INPUTS="true",
        LANGSMITH_HIDE_OUTPUTS="true",
    )
    import logfire
    from langgraph.checkpoint.postgres import PostgresSaver

    from langgraph_report.graph import build_graph

    logfire.configure(
        service_name="langgraph-report",
        send_to_logfire=bool(os.getenv("LOGFIRE_TOKEN")),
        console=False,
    )
    database = os.getenv("LANGGRAPH_DATABASE_URL") or "postgresql://weather:weather-local@127.0.0.1:55432/weather"
    with PostgresSaver.from_conn_string(database) as saver:
        saver.setup()
        graph = build_graph(saver)
        config = {
            "configurable": {"thread_id": args.run_id},
            "metadata": {
                "durable.runtime": "langgraph",
                "durable.run_id": args.run_id,
                "durable.command": args.command,
            },
        }
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
            result = graph.invoke(run_input, config, durability="sync")
        write_report(args.output, result["results"])
