import asyncio
from pathlib import Path
from typing import Annotated

import typer

from temporal_report.commands import resume, run, status, worker

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.command("run")
def run_command(run_id: str, output: Annotated[Path | None, typer.Option("--output")] = None) -> None:
    asyncio.run(run(run_id, output))


@app.command("resume")
def resume_command(run_id: str, output: Annotated[Path | None, typer.Option("--output")] = None) -> None:
    asyncio.run(resume(run_id, output))


@app.command("status")
def status_command(run_id: str, as_json: Annotated[bool, typer.Option("--json")] = False) -> None:
    asyncio.run(status(run_id, as_json))


@app.command("worker")
def worker_command() -> None:
    asyncio.run(worker())
