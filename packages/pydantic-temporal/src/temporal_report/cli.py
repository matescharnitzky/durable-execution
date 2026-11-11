import asyncio
import json
from pathlib import Path
from textwrap import shorten
from typing import Annotated

import logfire
import typer
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from rich.console import Console
from rich.table import Table
from rich.text import Text
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.service import RPCError, RPCStatusCode
from temporalio.worker import Worker

from temporal_report.config import Settings
from temporal_report.workflow import WeatherReport
from weather_core.report import write_report

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


def configure_telemetry() -> None:
    settings = Settings()
    logfire.configure(service_name="temporal-report", send_to_logfire=settings.logfire_token is not None, console=False)


async def connect() -> Client:
    return await Client.connect(
        Settings().temporal_address, plugins=[PydanticAIPlugin()], interceptors=[TracingInterceptor()],
    )


async def export(run_id: str, output: Path | None, *, start: bool) -> None:
    client = await connect()
    with logfire.span("Temporal report", **{"durable.runtime": "temporal", "durable.run_id": run_id}):
        if start:
            handle = await client.start_workflow(
                WeatherReport.run, id=run_id, task_queue=Settings().temporal_task_queue,
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )
        else:
            handle = client.get_workflow_handle(run_id)
        result = await handle.result()
        path = write_report(output, result, experiment="Temporal")
        typer.echo(f"Report saved to {path.resolve()}", err=True)


@app.command()
def run(run_id: str, output: Annotated[Path | None, typer.Option("--output")] = None) -> None:
    configure_telemetry()
    asyncio.run(export(run_id, output, start=True))


@app.command()
def resume(run_id: str, output: Annotated[Path | None, typer.Option("--output")] = None) -> None:
    configure_telemetry()
    asyncio.run(export(run_id, output, start=False))


async def inspect(run_id: str, as_json: bool) -> None:
    client = await connect()
    handle = client.get_workflow_handle(run_id)
    try:
        description = await handle.describe()
    except RPCError as error:
        if error.status != RPCStatusCode.NOT_FOUND:
            raise
        typer.echo(json.dumps({"run_id": run_id, "state": "unknown", "worker_started": False}) if as_json else "Unknown run ID.")
        return
    native = description.status.name
    state = {"RUNNING": "pending", "COMPLETED": "complete"}.get(native, "failed")
    history = await handle.fetch_history()
    rows = []
    started = False
    for event in history.events:
        if event.HasField("activity_task_scheduled_event_attributes"):
            attrs = event.activity_task_scheduled_event_attributes
            rows.append((str(event.event_id), "Scheduled", attrs.activity_type.name))
        elif event.HasField("activity_task_started_event_attributes"):
            started = True
            rows.append((str(event.event_id), "Started", f"Attempt {event.activity_task_started_event_attributes.attempt}"))
        elif event.HasField("activity_task_completed_event_attributes"):
            values = await client.data_converter.decode(event.activity_task_completed_event_attributes.result.payloads)
            rows.append((str(event.event_id), "Completed", shorten(str(values), width=240, placeholder="…")))
        elif event.HasField("activity_task_timed_out_event_attributes"):
            rows.append((str(event.event_id), "Timed out", event.activity_task_timed_out_event_attributes.failure.message))
        elif event.HasField("activity_task_failed_event_attributes"):
            rows.append((str(event.event_id), "Failed", event.activity_task_failed_event_attributes.failure.message))
    for pending in description.raw_description.pending_activities:
        active = pending.HasField("last_started_time")
        started = started or active
        rows.append((pending.activity_id, "Pending", f"{pending.activity_type.name} · attempt {pending.attempt}"))
    if as_json:
        typer.echo(json.dumps({"run_id": run_id, "state": state, "workflow_status": native, "worker_started": started}))
        return
    console = Console()
    console.print(f"Run: {run_id}\nState: {state} · Temporal: {native}", markup=False)
    table = Table(title="Native Temporal activity history", header_style="bold cyan")
    table.add_column("Event / activity")
    table.add_column("State")
    table.add_column("Saved details", max_width=96)
    for row in rows:
        table.add_row(*(Text(value) for value in row))
    console.print(table)


@app.command()
def status(run_id: str, as_json: Annotated[bool, typer.Option("--json")] = False) -> None:
    configure_telemetry()
    asyncio.run(inspect(run_id, as_json))


async def run_worker() -> None:
    client = await connect()
    await Worker(client, task_queue=Settings().temporal_task_queue, workflows=[WeatherReport]).run()


@app.command()
def worker() -> None:
    configure_telemetry()
    asyncio.run(run_worker())
