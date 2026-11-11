import json
from contextlib import contextmanager
from pathlib import Path
from textwrap import shorten
from typing import Annotated

import logfire
import typer
from dbos import DBOS, DBOSClient, SetWorkflowID
from rich.console import Console
from rich.table import Table
from rich.text import Text
from sqlalchemy.exc import ProgrammingError

from dbos_report.agent import report
from dbos_report.config import Settings
from weather_core.report import validate_report, write_report

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@contextmanager
def dbos_runtime():
    settings = Settings()
    logfire.configure(service_name="dbos-report", send_to_logfire=settings.logfire_token is not None, console=False)
    DBOS(config={
        "name": "weather-report",
        "system_database_url": settings.database_url,
        "dbos_system_schema": "dbos",
        "enable_otlp": True,
        "otel_attribute_format": "semconv",
    })
    DBOS.launch()
    try:
        yield
    finally:
        DBOS.destroy()


def save_report(output: Path | None, answer: dict) -> None:
    path = write_report(output, validate_report(answer), experiment="DBOS")
    typer.echo(f"Report saved to {path.resolve()}", err=True)


@app.command()
def run(run_id: str, output: Annotated[Path | None, typer.Option("--output")] = None) -> None:
    with dbos_runtime():
        if DBOS.get_workflow_status(run_id):
            raise typer.BadParameter("Run ID already exists. Use resume.", param_hint="run_id")
        with SetWorkflowID(run_id):
            handle = DBOS.start_workflow(report, run_id)
        save_report(output, handle.get_result())


@app.command()
def status(run_id: str, as_json: Annotated[bool, typer.Option("--json")] = False) -> None:
    client = DBOSClient(system_database_url=Settings().database_url, dbos_system_schema="dbos")
    try:
        try:
            workflows = client.list_workflows(workflow_ids=[run_id], load_input=False, load_output=False)
        except ProgrammingError as error:
            if getattr(error.orig, "sqlstate", None) != "42P01":
                raise
            workflows = []
        native = workflows[0].status if workflows else "UNKNOWN"
        state = {"SUCCESS": "complete", "UNKNOWN": "unknown", "ERROR": "failed", "CANCELLED": "failed", "MAX_RECOVERY_ATTEMPTS_EXCEEDED": "failed"}.get(native, "pending")
        steps = client.list_workflow_steps(run_id, load_output=not as_json) if workflows else []
        if as_json:
            typer.echo(json.dumps({"run_id": run_id, "state": state, "workflow_status": native}))
            return
        console = Console()
        console.print(f"Run: {run_id}\nState: {state} · DBOS: {native}", markup=False)
        table = Table(title="Steps saved in PostgreSQL", header_style="bold cyan")
        table.add_column("Step", justify="right")
        table.add_column("Function")
        table.add_column("Saved result", max_width=96)
        for step in steps:
            table.add_row(
                str(step["function_id"]), Text(step["function_name"]),
                Text(shorten(str(step["error"] or step["output"] or "—"), width=240, placeholder="…")),
            )
        console.print(table)
    finally:
        client.destroy()


@app.command()
def resume(run_id: str, output: Annotated[Path | None, typer.Option("--output")] = None) -> None:
    with dbos_runtime():
        state = DBOS.get_workflow_status(run_id)
        if state is None:
            raise typer.BadParameter("Unknown run ID.", param_hint="run_id")
        handle = DBOS.resume_workflow(run_id) if state.status in {"ERROR", "CANCELLED", "SUSPENDED", "MAX_RECOVERY_ATTEMPTS_EXCEEDED"} else DBOS.retrieve_workflow(run_id)
        save_report(output, handle.get_result())
