"""Command-line interface for operational tasks."""

from __future__ import annotations

import asyncio

import typer

from src.tasks import release_summary
from src.core.container import get_container

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


@app.command("sync-sonarr-requests")
def sync_sonarr_requests_command() -> None:
    """Synchronise Sonarr missing seasons into media requests."""

    container = get_container()
    container.startup()
    try:
        use_case = container.use_cases.media_requests.sync_sonarr
        result = asyncio.run(use_case.execute())
    finally:
        container.shutdown()

    typer.echo(
        "Sonarr sync complete "
        f"(created={result.created}, updated={result.updated}, completed={result.completed})"
    )


@app.command("sync-releases")
def sync_releases_command() -> None:
    """Synchronise release stats from qBittorrent."""
    from src.tasks.sync_releases import SyncReleasesTask
    from src.infrastructure.qbittorrent import QbittorrentClient

    container = get_container()
    settings = container.settings
    
    if not settings.qbittorrent_url or not settings.qbittorrent_username:
        typer.echo("qBittorrent not configured. Set RELEASARR_QBITTORRENT_* env vars.")
        raise typer.Exit(code=1)
    
    container.startup()
    try:
        client = QbittorrentClient(
            base_url=settings.qbittorrent_url,
            username=settings.qbittorrent_username,
            password=settings.qbittorrent_password,
            timeout=settings.qbittorrent_timeout,
        )
        task = SyncReleasesTask(
            db=container.db_manager,
            client=client,
            category=settings.qbittorrent_category,
        )
        result = asyncio.run(task.execute())
    finally:
        container.shutdown()

    typer.echo(
        f"Release sync complete (synced={result.synced}, failed={result.failed}, not_found={result.not_found})"
    )


def main() -> None:  # pragma: no cover - Typer handles exit
    """Entry point used by `python -m` invocations."""

    typer.main.get_command(app)()


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
