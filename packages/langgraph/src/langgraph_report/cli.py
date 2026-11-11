import json
from contextlib import contextmanager
from pathlib import Path
from textwrap import shorten
from typing import Annotated

import typer
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from rich.console import Console
from rich.table import Table
from rich.text import Text

from langgraph_report.config import Settings
from langgraph_report.observability import configure_telemetry
from langgraph_report.tools import web_search
from weather_core.prompts import SYSTEM_PROMPT
from weather_core.report import validate_report, write_report

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@contextmanager
def langgraph_agent(run_id: str, command: str):
    settings = Settings()
    configure_telemetry(settings)
    with PostgresSaver.from_conn_string(settings.database_url) as saver:
        saver.setup()
        agent = create_agent(
            model=ChatOpenAI(model=settings.openai_model),
            tools=[web_search],
            system_prompt=SYSTEM_PROMPT,
            checkpointer=saver,
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


def save_report(output: Path | None, messages) -> None:
    answer = messages[-1].text.strip().removeprefix("```json").removesuffix("```").strip()
    report = validate_report(json.loads(answer))
    path = write_report(output, report, experiment="LangGraph")
    typer.echo(f"Report saved to {path.resolve()}", err=True)


@app.command()
def run(
    run_id: str,
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    with langgraph_agent(run_id, "run") as (agent, config):
        if agent.get_state(config).values:
            raise typer.BadParameter("Run ID already exists. Use resume.", param_hint="run_id")
        result = agent.invoke(
            {"messages": [HumanMessage("Generate the weather report.")]},
            config,
            durability="sync", # it saves the checkpoint before the next step starts. Async would save the previous step and run the next at the same time. 
        )
        save_report(output, result["messages"])


@app.command()
def status(
    run_id: str,
    as_json: Annotated[bool, typer.Option("--json", help="Return machine-readable status")] = False,
) -> None:
    with langgraph_agent(run_id, "status") as (agent, config):
        state = agent.get_state(config)
        messages = state.values.get("messages", [])
        complete = bool(messages) and isinstance(messages[-1], AIMessage) and not state.next
        summary = {
            "run_id": run_id,
            "state": ("complete" if complete else "pending") if state.values else "unknown",
            "next": list(state.next),
        }
        if as_json:
            typer.echo(json.dumps(summary))
            return

        console = Console()
        console.print(f"Run: {run_id}", markup=False)
        console.print(f"State: {summary['state']} · Next: {', '.join(state.next) or '—'}", markup=False)
        if not messages:
            console.print("No saved turns.")
            return

        table = Table(title="Turns saved in PostgreSQL", header_style="bold cyan")
        table.add_column("Turn", justify="right")
        table.add_column("Type")
        table.add_column("Saved content", max_width=96)
        for number, message in enumerate(messages, start=1):
            kind = "User" if isinstance(message, HumanMessage) else "Model"
            content = message.text
            if isinstance(message, AIMessage) and message.tool_calls:
                kind = "Model → tool"
                content = f"{len(message.tool_calls)} tool call(s): " + "\n".join(
                    f"{call['name']}({json.dumps(call['args'], ensure_ascii=False)})"
                    for call in message.tool_calls
                )
            elif isinstance(message, ToolMessage):
                kind = f"Tool: {message.name or 'result'}"
            table.add_row(str(number), Text(kind), Text(shorten(content, width=240, placeholder="…")))
        console.print(table)


@app.command()
def resume(
    run_id: str,
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    with langgraph_agent(run_id, "resume") as (agent, config):
        state = agent.get_state(config)
        if not state.values:
            raise typer.BadParameter("Unknown run ID.", param_hint="run_id")
        result = agent.invoke(None, config, durability="sync") if state.next else state.values
        save_report(output, result["messages"])
