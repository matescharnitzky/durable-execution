import argparse
import json
from datetime import date
from pathlib import Path

from langgraph_report.config import Settings
from langgraph_report.observability import configure_telemetry
from langgraph_report.report import batches, write_report


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="langgraph-report")
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


def main() -> None:
    args = arguments()
    settings = Settings()
    configure_telemetry(settings)

    from langgraph.checkpoint.postgres import PostgresSaver

    from langgraph_report.graph import build_agent

    with PostgresSaver.from_conn_string(settings.database_url) as saver:
        saver.setup()
        agent = build_agent(saver, settings)
        config = {
            "configurable": {"thread_id": args.run_id},
            "metadata": {
                "durable.runtime": "langgraph",
                "durable.run_id": args.run_id,
                "durable.command": args.command,
            },
        }
        state = agent.get_state(config)
        completed = len(state.values.get("results", []))
        complete = bool(state.values) and completed == len(state.values["batches"])
        if args.command == "status":
            print(json.dumps({
                "run_id": args.run_id,
                "state": ("complete" if complete else "pending") if state.values else "unknown",
                "completed_batches": completed,
                "next": list(state.next),
            }))
            return
        if args.command == "run":
            if state.values:
                raise SystemExit("Run ID already exists. Use resume.")
            run_input = {
                "messages": [],
                "forecast_date": args.date.isoformat(),
                "batches": batches(args.fixture),
                "results": [],
            }
        else:
            if not state.values:
                raise SystemExit("Unknown run ID.")
            run_input = None
            if not complete and (not state.next or "forecast" in state.next):
                # The earlier graph used a different pending node. Keep its committed batches.
                run_input = {**state.values, "messages": []}
        result = state.values
        if not complete:
            result = agent.invoke(run_input, config, durability="sync")
        write_report(args.output, result["results"])
