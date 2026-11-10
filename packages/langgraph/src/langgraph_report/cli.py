import json
import sys

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver

from langgraph_report.arguments import arguments

from langgraph_report.config import Settings
from langgraph_report.observability import configure_telemetry
from langgraph_report.prompts import load_search_config
from langgraph_report.report import report_cities, validate_report, write_report
from langgraph_report.tools import forecast_model, web_search_tool


def main() -> None:
    args = arguments()
    settings = Settings()
    configure_telemetry(settings)

    with PostgresSaver.from_conn_string(settings.database_url) as saver:
        saver.setup()
        model = forecast_model(settings)
        agent = create_agent(
            model=model,
            tools=[web_search_tool(model)],
            system_prompt=(
                "Call web_search to collect forecasts and source URLs before writing the report. "
                + load_search_config().instructions
            ),
            checkpointer=saver,
            name="Weather report",
        )
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
        print(f"Report saved to {args.output.resolve()}", file=sys.stderr)
