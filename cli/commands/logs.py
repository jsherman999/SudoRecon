"""Log search commands for CLI."""

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def logs():
    """Search and export sudo logs."""
    pass


@logs.command()
@click.argument("query", required=False)
@click.option("--user", help="Filter by username")
@click.option("--host", help="Filter by hostname")
@click.option("--result", type=click.Choice(["ACCEPT", "DENY"]), help="Filter by result")
@click.option("--limit", default=50, help="Number of results to show")
@click.pass_context
def search(ctx, query, user, host, result, limit):
    """Search sudo logs."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    headers = {"X-API-Key": api_key}
    params = {"page_size": limit}

    if query:
        params["q"] = query
    if user:
        params["username"] = user
    if host:
        params["hostname"] = host
    if result:
        params["result"] = result

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{api_url}/api/v1/logs",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            table = Table(title="Sudo Logs")
            table.add_column("Timestamp", style="cyan")
            table.add_column("Server", style="green")
            table.add_column("User")
            table.add_column("Result")
            table.add_column("Command")

            for log in data["results"]:
                # Truncate command if too long
                command = log["command"]
                if len(command) > 50:
                    command = command[:47] + "..."

                result_style = "green" if log["result"] == "ACCEPT" else "red"
                table.add_row(
                    log["timestamp"][:19],  # Strip milliseconds
                    log.get("server_hostname", "unknown"),
                    log["username"],
                    f"[{result_style}]{log['result']}[/{result_style}]",
                    command,
                )

            console.print(table)
            console.print(f"\nShowing {len(data['results'])} of {data['total']} results")

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()


@logs.command()
@click.pass_context
def stats(ctx):
    """Show log statistics."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    headers = {"X-API-Key": api_key}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{api_url}/api/v1/logs/stats",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            table = Table(title="Log Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Total Logs", str(data["total_logs"]))
            table.add_row("Accepted", str(data["accept_count"]))
            table.add_row("Denied", str(data["deny_count"]))
            table.add_row("Unique Users", str(data["unique_users"]))
            table.add_row("Unique Servers", str(data["unique_servers"]))

            if data.get("time_range_start"):
                table.add_row("Earliest Log", data["time_range_start"][:19])
            if data.get("time_range_end"):
                table.add_row("Latest Log", data["time_range_end"][:19])

            console.print(table)

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()
