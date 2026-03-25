"""
MEMANTO CLI - Config commands (show).
"""

from rich.table import Table

from memanto.cli.commands._shared import (
    config_app,
    config_manager,
    console,
)


@config_app.command("show")
def config_show():
    """Display current configuration."""
    api_key = config_manager.get_api_key()
    server_cfg = config_manager.get_server_config()
    cli_cfg = config_manager.get_cli_config()
    active_agent_id, active_session_token = config_manager.get_active_session()
    schedule_time = config_manager.get_schedule_time()

    table = Table(title="MEMANTO Configuration", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Config Dir", str(config_manager.config_dir))
    table.add_row("Server URL", f"{server_cfg['url']}:{server_cfg['port']}")
    table.add_row("API Key", "***configured***" if api_key else "not set")
    table.add_row("Active Agent", active_agent_id or "none")
    table.add_row("Session Active", "yes" if active_session_token else "no")
    table.add_row("Schedule Time", schedule_time)
    table.add_row("Interactive Mode", str(cli_cfg.get("interactive_mode", True)))
    table.add_row("Smart Parse", str(cli_cfg.get("smart_parse", True)))

    console.print(table)
