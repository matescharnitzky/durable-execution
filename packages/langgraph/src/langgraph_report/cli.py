from pathlib import Path
from typing import Annotated

import typer

from langgraph_report.commands import resume, run, status

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.command("run")
def run_command(
    run_id: str, output: Annotated[Path | None, typer.Option("--output")] = None
) -> None:
    """Generate a weather report under a new run ID."""
    run(run_id, output)


@app.command("status")
def status_command(
    run_id: str,
    as_json: Annotated[bool, typer.Option("--json", help="Return machine-readable status")] = False,
) -> None:
    """Show saved execution state as a table or JSON."""
    status(run_id, as_json)


@app.command("resume")
def resume_command(
    run_id: str, output: Annotated[Path | None, typer.Option("--output")] = None
) -> None:
    """Resume a saved run and export its report."""
    resume(run_id, output)
