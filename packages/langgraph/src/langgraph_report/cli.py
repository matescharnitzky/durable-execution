import argparse
import json
from datetime import date
from pathlib import Path

from langgraph_report.config import Settings
from langgraph_report.observability import configure_telemetry
from langgraph_report.report import report_cities, validate_report, write_report


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
            command.add_argument("--fixture", action="store_true", help="Use the two fixture cities")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    settings = Settings()
    configure_telemetry(settings)

    from langchain_core.messages import AIMessage, HumanMessage
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
        messages = state.values.get("messages", [])
        complete = bool(messages) and isinstance(messages[-1], AIMessage) and not state.next
        if args.command == "status":
            print(json.dumps({
                "run_id": args.run_id,
                "state": ("complete" if complete else "pending") if state.values else "unknown",
                "next": list(state.next),
            }))
            return

        run_input = None
        if args.command == "run":
            if state.values:
                raise SystemExit("Run ID already exists. Use resume.")
            request = {"forecast_date": args.date.isoformat(), "cities": report_cities(args.fixture)}
            run_input = {"messages": [HumanMessage(json.dumps(request))]}
        elif not state.values:
            raise SystemExit("Unknown run ID.")

        if not complete:
            messages = agent.invoke(run_input, config, durability="sync")["messages"]
        request = json.loads(messages[0].text)
        answer = messages[-1].text.strip().removeprefix("```json").removesuffix("```").strip()
        report = validate_report(json.loads(answer), request["forecast_date"], request["cities"])
        write_report(args.output, [report])
