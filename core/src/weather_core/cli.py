import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from weather_core.report import validate_report, write_report

app = typer.Typer(pretty_exceptions_show_locals=False)


@app.command()
def render(
    experiment: str, output: Annotated[Path | None, typer.Option("--output")] = None
) -> None:
    """Render a final JSON report from stdin using the shared template."""
    path = write_report(output, validate_report(json.load(sys.stdin)), experiment=experiment)
    typer.echo(str(path.resolve()))
