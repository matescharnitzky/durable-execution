import json
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver

from langgraph_report.config import Settings
from langgraph_report.observability import configure_telemetry
from langgraph_report.report import validate_report, write_report
from langgraph_report.tools import web_search
from weather_core.prompts import SYSTEM_PROMPT

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@contextmanager
def report_agent(run_id: str, command: str):
    settings = Settings()
    configure_telemetry(settings)
    with PostgresSaver.from_conn_string(settings.database_url) as saver:
        saver.setup()
        agent = create_agent(
            model=ChatOpenAI(model=settings.openai_model),
            tools=[web_search],
            system_prompt=(
                "Call web_search to collect forecasts and source URLs before writing the report. "
                + SYSTEM_PROMPT
            ),
            checkpointer=saver,
            name="Weather report",
        )
        config = {
            "configurable": {"thread_id": run_id},
            "metadata": {
                "durable.runtime": "langgraph",
                "durable.run_id": run_id,
                "durable.command": command,
            },
        }
        yield agent, config


def save_report(output: Path, messages) -> None:
    answer = messages[-1].text.strip().removeprefix("```json").removesuffix("```").strip()
    report = validate_report(json.loads(answer))
    write_report(output, [report])
    typer.echo(f"Report saved to {output.resolve()}", err=True)


@app.command()
def run(
    run_id: str,
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    with report_agent(run_id, "run") as (agent, config):
        if agent.get_state(config).values:
            raise typer.BadParameter("Run ID already exists. Use resume.", param_hint="run_id")
        result = agent.invoke(
            {"messages": [HumanMessage("Generate the weather report.")]},
            config,
            durability="sync",
        )
        save_report(output, result["messages"])


@app.command()
def status(run_id: str) -> None:
    with report_agent(run_id, "status") as (agent, config):
        state = agent.get_state(config)
        messages = state.values.get("messages", [])
        complete = bool(messages) and isinstance(messages[-1], AIMessage) and not state.next
        typer.echo(json.dumps({
            "run_id": run_id,
            "state": ("complete" if complete else "pending") if state.values else "unknown",
            "next": list(state.next),
        }))


@app.command()
def resume(
    run_id: str,
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    with report_agent(run_id, "resume") as (agent, config):
        state = agent.get_state(config)
        if not state.values:
            raise typer.BadParameter("Unknown run ID.", param_hint="run_id")
        result = agent.invoke(None, config, durability="sync") if state.next else state.values
        save_report(output, result["messages"])
