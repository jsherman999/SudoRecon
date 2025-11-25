"""SudoGuard CLI main entry point."""

import click

from cli.commands import logs, scan, servers


@click.group()
@click.option("--api-url", default="http://localhost:8080", help="API base URL")
@click.option("--api-key", envvar="SUDOGUARD_API_KEY", help="API key for authentication")
@click.option(
    "--output",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format",
)
@click.option("--quiet", is_flag=True, help="Suppress non-essential output")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.version_option(version="1.0.0")
@click.pass_context
def cli(ctx, api_url, api_key, output, quiet, verbose):
    """SudoGuard - Centralized sudo management and log analysis."""
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url
    ctx.obj["api_key"] = api_key
    ctx.obj["output"] = output
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose


# Register command groups
cli.add_command(scan.scan)
cli.add_command(servers.servers)
cli.add_command(logs.logs)


if __name__ == "__main__":
    cli(obj={})
