import asyncio
from pathlib import Path
from typing import Annotated

import typer

from absurd_report import commands

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.callback()
def configure() -> None:
    """Configure tracing without recording model content."""
    commands.configure()


@app.command("install")
def install() -> None:
    """Initialize native storage."""
    asyncio.run(commands.install())


@app.command("worker")
def worker() -> None:
    """Run or replace a native worker."""
    asyncio.run(commands.worker())


@app.command("run")
def run(run_id: str, output: Annotated[Path | None, typer.Option("--output")] = None) -> None:
    """Start a report, printing its native task ID before waiting."""
    asyncio.run(commands.run(run_id, output))


@app.command("resume")
def resume(task_id: str, output: Annotated[Path | None, typer.Option("--output")] = None) -> None:
    """Follow or re-export the original native task."""
    asyncio.run(commands.resume(task_id, output))


@app.command("status")
def status(task_id: str, as_json: Annotated[bool, typer.Option("--json")] = False) -> None:
    """Show native status as text or JSON."""
    asyncio.run(commands.status(task_id, as_json))
