"""Command-line interface for operational tasks."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import typer

from src.tasks import release_summary

app = typer.Typer(help="Operational task runner")


@app.command("release-summary")
def release_summary_command(json_output: bool = typer.Option(False, "--json")) -> None:
    """Print aggregated release summary information."""

    summary = asyncio.run(release_summary.generate_summary())
    if json_output:
        typer.echo(release_summary.format_summary(summary))
        return

    typer.echo("Release Summary")
    typer.echo(f"Total: {summary.total}")
    for status, count in summary.by_status.items():
        typer.echo(f" - {status.value}: {count}")


def main() -> None:  # pragma: no cover - Typer handles exit
    """Entry point used by `python -m` invocations."""

    typer.main.get_command(app)()


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
