"""Scan commands for CLI."""

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def scan():
    """Scan servers for sudo logs."""
    pass


@scan.command()
@click.argument("hostname")
@click.option("--since", help="Start date for log collection")
@click.option("--until", help="End date for log collection")
@click.option("--include-denied/--no-denied", default=True, help="Include denied commands")
@click.pass_context
def single(ctx, hostname, since, until, include_denied):
    """Scan a single server."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required. Set SUDOGUARD_API_KEY or use --api-key", err=True)
        raise click.Abort()

    # Prepare request
    payload = {
        "hostname": hostname,
        "options": {
            "include_denied": include_denied,
        },
    }

    headers = {"X-API-Key": api_key}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{api_url}/api/v1/scan/single",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            console.print(f"[green]Scan job created:[/green] {data['job_id']}")
            console.print(f"Status: {data['status']}")
            console.print(f"Check status at: {data['status_url']}")

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()


@scan.command()
@click.argument("group_id", type=int)
@click.option("--threads", default=50, help="Number of parallel threads")
@click.pass_context
def group(ctx, group_id, threads):
    """Scan all servers in a group."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    payload = {"group_id": group_id, "thread_count": threads}
    headers = {"X-API-Key": api_key}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{api_url}/api/v1/scan/group",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            console.print(f"[green]Scan job created:[/green] {data['job_id']}")
            console.print(f"Message: {data['message']}")

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()


@scan.command()
@click.argument("job_id")
@click.pass_context
def status(ctx, job_id):
    """Check status of a scan job."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    headers = {"X-API-Key": api_key}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{api_url}/api/v1/scan/jobs/{job_id}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            table = Table(title=f"Scan Job: {job_id}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Status", data["status"])
            table.add_row("Type", data["job_type"])
            table.add_row("Target", data["target_spec"])
            table.add_row("Progress", f"{data['progress']}%")
            table.add_row("Total Hosts", str(data["total_hosts"]))
            table.add_row("Completed", str(data["completed_hosts"]))
            table.add_row("Failed", str(data["failed_hosts"]))

            console.print(table)

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()
