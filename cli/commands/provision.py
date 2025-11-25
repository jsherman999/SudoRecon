"""Provision management commands for CLI."""

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def provision():
    """Manage sudo provisions."""
    pass


@provision.command()
@click.option("--status", help="Filter by status")
@click.option("--jit", is_flag=True, help="Show only JIT provisions")
@click.pass_context
def list(ctx, status, jit):
    """List all provisions."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    headers = {"X-API-Key": api_key}
    params = {}
    if status:
        params["status"] = status
    if jit:
        params["is_jit"] = "true"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{api_url}/api/v1/provisions",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            table = Table(title="Sudo Provisions")
            table.add_column("ID", style="cyan")
            table.add_column("Principal", style="green")
            table.add_column("Server")
            table.add_column("Status")
            table.add_column("JIT")
            table.add_column("Expires")

            for prov in data["results"]:
                expires = prov.get("grant_end")
                if expires:
                    expires = expires[:16].replace("T", " ")
                else:
                    expires = "Never"

                status_style = "green" if prov["status"] == "active" else "yellow"
                table.add_row(
                    str(prov["id"]),
                    prov["principal_name"],
                    prov.get("server_hostname", "unknown"),
                    f"[{status_style}]{prov['status']}[/{status_style}]",
                    "✓" if prov["is_jit"] else "",
                    expires,
                )

            console.print(table)
            console.print(f"\nTotal: {data['total']} provisions")

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()


@provision.command()
@click.option("--server", required=True, type=int, help="Server ID")
@click.option("--user", help="Username")
@click.option("--group", help="AD group name")
@click.option("--rule", default="ALL=(ALL) ALL", help="Sudo rule")
@click.option("--expires", help="Expiration date (YYYY-MM-DD)")
@click.option("--justification", required=True, help="Justification")
@click.option("--ticket", help="Ticket reference")
@click.pass_context
def grant(ctx, server, user, group, rule, expires, justification, ticket):
    """Grant sudo access to a user or group."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    if not user and not group:
        click.echo("Error: Must specify either --user or --group", err=True)
        raise click.Abort()

    payload = {
        "servers": [server],
        "principal_type": "group" if group else "user",
        "principal_name": group if group else user,
        "sudo_rule": rule,
        "is_jit": False,
        "justification": justification,
    }

    if expires:
        payload["grant_end"] = f"{expires}T23:59:59Z"
    if ticket:
        payload["ticket_reference"] = ticket

    headers = {"X-API-Key": api_key}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{api_url}/api/v1/provisions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            if data:
                prov = data[0]
                console.print(f"[green]Provision created:[/green] ID {prov['id']}")
                console.print(f"Principal: {prov['principal_name']}")
                console.print(f"Status: {prov['status']}")

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()


@provision.command()
@click.option("--server", required=True, type=int, help="Server ID")
@click.option("--user", help="Username")
@click.option("--group", help="AD group name")
@click.option("--duration", default=60, help="Duration in minutes")
@click.option("--rule", default="ALL=(ALL) ALL", help="Sudo rule")
@click.option("--justification", required=True, help="Justification")
@click.pass_context
def jit(ctx, server, user, group, duration, rule, justification):
    """Create just-in-time sudo access."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    if not user and not group:
        click.echo("Error: Must specify either --user or --group", err=True)
        raise click.Abort()

    payload = {
        "server_id": server,
        "principal_type": "group" if group else "user",
        "principal_name": group if group else user,
        "sudo_rule": rule,
        "duration_minutes": duration,
        "justification": justification,
        "auto_expire": True,
    }

    headers = {"X-API-Key": api_key}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{api_url}/api/v1/provisions/jit",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            console.print(f"[green]JIT access granted:[/green] {data['message']}")
            console.print(f"Provision ID: {data['provision_id']}")
            console.print(f"Expires at: {data['expires_at'][:19]}")

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()


@provision.command()
@click.argument("provision_id", type=int)
@click.option("--reason", help="Revocation reason")
@click.pass_context
def revoke(ctx, provision_id, reason):
    """Revoke a sudo provision."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    if not click.confirm(f"Are you sure you want to revoke provision {provision_id}?"):
        raise click.Abort()

    headers = {"X-API-Key": api_key}
    payload = {}
    if reason:
        payload["reason"] = reason

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(
                f"{api_url}/api/v1/provisions/{provision_id}",
                headers=headers,
                json=payload if payload else None,
            )
            response.raise_for_status()
            data = response.json()

            console.print(f"[green]{data['message']}[/green]")

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()


@provision.command()
@click.option("--hours", default=24, help="Hours ahead to check")
@click.pass_context
def expiring(ctx, hours):
    """Show provisions expiring soon."""
    api_url = ctx.obj["api_url"]
    api_key = ctx.obj["api_key"]

    if not api_key:
        click.echo("Error: API key required", err=True)
        raise click.Abort()

    headers = {"X-API-Key": api_key}
    params = {"hours": hours}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{api_url}/api/v1/provisions/expiring",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                console.print(f"No provisions expiring in the next {hours} hours")
                return

            table = Table(title=f"Provisions Expiring in {hours} Hours")
            table.add_column("ID", style="cyan")
            table.add_column("Principal", style="yellow")
            table.add_column("Server")
            table.add_column("Expires", style="red")

            for prov in data:
                expires = prov["grant_end"][:16].replace("T", " ")
                table.add_row(
                    str(prov["id"]),
                    prov["principal_name"],
                    prov.get("server_hostname", "unknown"),
                    expires,
                )

            console.print(table)

    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise click.Abort()
