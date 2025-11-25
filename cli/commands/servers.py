"""Server management commands for CLI."""

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def servers():
    """Manage server inventory."""
    pass


@servers.command()
@click.option("--status", help="Filter by status")
@click.pass_context
def list(ctx, status):
    """List all servers."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    headers = {"X-API-Key": api_key}
    params = {}
    if status:
        params["status"] = status

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{api_url}/api/v1/servers",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            table = Table(title="Servers")
            table.add_column("ID", style="cyan")
            table.add_column("Hostname", style="green")
            table.add_column("FQDN")
            table.add_column("Status")
            table.add_column("Last Scan")

            for server in data["results"]:
                table.add_row(
                    str(server["id"]),
                    server["hostname"],
                    server["fqdn"],
                    server["status"],
                    server.get("last_scan_at", "Never") or "Never",
                )

            console.print(table)
            console.print(f"\nTotal: {data['total']} servers")

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()


@servers.command()
@click.argument("fqdn")
@click.pass_context
def add(ctx, fqdn):
    """Add a new server."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    hostname = fqdn.split(".")[0]
    payload = {"hostname": hostname, "fqdn": fqdn}
    headers = {"X-API-Key": api_key}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{api_url}/api/v1/servers",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            console.print(f"[green]Server added:[/green] {data['fqdn']} (ID: {data['id']})")

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()


@servers.command()
@click.argument("server_id", type=int)
@click.pass_context
def remove(ctx, server_id):
    """Remove a server."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    if not click.confirm(f"Are you sure you want to remove server {server_id}?"):
        raise click.Abort()

    headers = {"X-API-Key": api_key}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(
                f"{api_url}/api/v1/servers/{server_id}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            console.print(f"[green]{data['message']}[/green]")

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()
