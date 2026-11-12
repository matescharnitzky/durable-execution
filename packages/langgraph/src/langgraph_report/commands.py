import json
from contextlib import contextmanager
from pathlib import Path
from textwrap import shorten

import typer
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.errors import UndefinedColumn, UndefinedTable
from rich.console import Console
from rich.table import Table
from rich.text import Text

from langgraph_report.config import Settings
from langgraph_report.observability import configure_telemetry
from langgraph_report.tools import web_search
from weather_core.prompts import SYSTEM_PROMPT
from weather_core.report import validate_report, write_report


@contextmanager
def langgraph_agent(run_id: str, command: str):
    """Yield a PostgreSQL-checkpointed agent and its run configuration."""
    settings = Settings()
    configure_telemetry(settings)
    with PostgresSaver.from_conn_string(settings.database_url) as saver:
        if command != "status":
            saver.setup()
        agent = create_agent(
            model=ChatOpenAI(
                model=settings.openai_model, model_kwargs={"parallel_tool_calls": False}
            ),
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
    """Validate the final assistant message and write its HTML report."""
    answer = messages[-1].text.strip().removeprefix("```json").removesuffix("```").strip()
    report = validate_report(json.loads(answer))
    path = write_report(output, report, experiment="LangGraph")
    typer.echo(f"Report saved to {path.resolve()}", err=True)


def run(
    run_id: str,
    output: Path | None = None,
) -> None:
    """Start a new checkpointed report and export the result."""
    with langgraph_agent(run_id, "run") as (agent, config):
        if agent.get_state(config).values:
            raise typer.BadParameter("Run ID already exists. Use resume.", param_hint="run_id")
        result = agent.invoke(
            {"messages": [HumanMessage("Generate the weather report.")]},
            config,
            durability="sync",  # Save the checkpoint before starting the next step.
        )
        save_report(output, result["messages"])


def status(
    run_id: str,
    as_json: bool = False,
) -> None:
    """Show saved messages and the next graph nodes for a run."""
    with langgraph_agent(run_id, "status") as (agent, config):
        try:
            state = agent.get_state(config)
        except (UndefinedTable, UndefinedColumn):
            # A new run may still be creating or migrating its checkpoint tables.
            if as_json:
                typer.echo(json.dumps({"run_id": run_id, "state": "unknown", "next": []}))
            else:
                typer.echo(f"Run: {run_id}\nState: unknown\nNo saved turns.")
            return
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
        console.print(
            f"State: {summary['state']} · Next: {', '.join(state.next) or '—'}", markup=False
        )
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
            table.add_row(
                str(number), Text(kind), Text(shorten(content, width=240, placeholder="…"))
            )
        console.print(table)


def resume(
    run_id: str,
    output: Path | None = None,
) -> None:
    """Continue from the saved checkpoint or export a completed report."""
    with langgraph_agent(run_id, "resume") as (agent, config):
        state = agent.get_state(config)
        if not state.values:
            raise typer.BadParameter("Unknown run ID.", param_hint="run_id")
        result = agent.invoke(None, config, durability="sync") if state.next else state.values
        save_report(output, result["messages"])
