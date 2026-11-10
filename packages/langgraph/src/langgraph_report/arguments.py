import argparse
from datetime import date
from pathlib import Path


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="langgraph-report")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "status", "resume"):
        command = commands.add_parser(name)
        command.add_argument("run_id")
        if name != "status":
            command.add_argument("--output", type=Path, required=True)
        if name == "run":
            command.add_argument("--date", type=date.fromisoformat, required=True)
            command.add_argument("--fixture", action="store_true", help="Use the two fixture cities")
    return parser.parse_args()
