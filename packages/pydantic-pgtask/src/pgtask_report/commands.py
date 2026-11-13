import json
from pathlib import Path

import logfire
import typer
from pgtask import Client, Worker

from pgtask_report.config import Settings
from pgtask_report.runtime import report, tasks
from weather_core.report import validate_report, write_report


def configure() -> None:
    """Configure content-free tracing for each command process."""
    logfire.configure(
        service_name="pgtask-report",
        send_to_logfire=Settings().logfire_token is not None,
        console=False,
    )


async def install() -> None:
    """Initialize the native queue after its database is provisioned."""
    client = await Client.connect(Settings().pgtask_database_url.get_secret_value())
    await client.migrate()


async def run(run_id: str, output: Path | None = None) -> None:
    """Enqueue with a stable idempotency key, then follow the native task."""
    client = await Client.connect(Settings().pgtask_database_url.get_secret_value())
    handle = await client.enqueue(report.request({"run_id": run_id}, idempotency_key=run_id))
    task_id = handle.id
    typer.echo(f"Task ID: {task_id}", err=True)
    await resume(task_id, output)


async def status(task_id: str, as_json: bool = False) -> None:
    """Show the native task state without starting a worker."""
    client = await Client.connect(Settings().pgtask_database_url.get_secret_value())
    snapshot = await client.task_result(task_id)
    native = snapshot.state if snapshot else "unknown"
    state = {
        "succeeded": "complete",
        "completed": "complete",
        "failed": "failed",
        "cancelled": "failed",
        "unknown": "unknown",
    }.get(native, "pending")
    result = {"task_id": task_id, "state": state, "task_status": native}
    typer.echo(
        json.dumps(result) if as_json else f"Task: {task_id}\nState: {state} · pgtask: {native}"
    )


async def resume(task_id: str, output: Path | None = None) -> None:
    """Follow the original task; a separate replacement worker replays saved steps."""
    client = await Client.connect(Settings().pgtask_database_url.get_secret_value())
    snapshot = await client.wait_result(task_id)
    if snapshot is None:
        raise typer.BadParameter("Unknown task ID.")
    if snapshot.state not in {"succeeded", "completed"}:
        raise typer.BadParameter(
            f"Task ended in {snapshot.state}; inspect native storage for details."
        )
    if not isinstance(snapshot.result, dict):
        raise ValueError("Native task result is not a report object")
    path = write_report(output, validate_report(snapshot.result), experiment="pgtask")
    typer.echo(f"Report saved to {path.resolve()}", err=True)


async def worker() -> None:
    """Run the native worker; restart this command after a crash."""
    await Worker(
        Settings().pgtask_database_url.get_secret_value(), tasks, retention_enabled=False
    ).run()
