"""
MEMANTO CLI - Welcome Banner Display

Beautiful startup display with Moorcheh blue-violet branding,
memory type taxonomy, and quick-start commands.
"""

import platform

from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from memanto.cli.config.manager import ConfigManager
from memanto.cli.ui.theme import (
    BOLD_BRIGHT,
    BOLD_PRIMARY,
    PRIMARY,
)

MEMANTO_VERSION = "0.1.0"

# ASCII art logo — clean block MemAnto
LOGO = r"""
 ███╗   ███╗ ███████╗ ███╗   ███╗  █████╗  ███╗   ██╗ ████████╗  ██████╗
 ████╗ ████║ ██╔════╝ ████╗ ████║ ██╔══██╗ ████╗  ██║ ╚══██╔══╝ ██╔═══██╗
 ██╔████╔██║ █████╗   ██╔████╔██║ ███████║ ██╔██╗ ██║    ██║    ██║   ██║
 ██║╚██╔╝██║ ██╔══╝   ██║╚██╔╝██║ ██╔══██║ ██║╚██╗██║    ██║    ██║   ██║
 ██║ ╚═╝ ██║ ███████╗ ██║ ╚═╝ ██║ ██║  ██║ ██║ ╚████║    ██║    ╚██████╔╝
 ╚═╝     ╚═╝ ╚══════╝ ╚═╝     ╚═╝ ╚═╝  ╚═╝ ╚═╝  ╚═══╝    ╚═╝     ╚═════╝
""".strip("\n")

# All 13 MEMANTO memory types
MEMORY_TYPES = [
    "fact",
    "preference",
    "goal",
    "decision",
    "artifact",
    "learning",
    "event",
    "instruction",
    "context",
    "observation",
    "commitment",
    "relationship",
    "error",
]


def print_logo() -> None:
    """Print the MEMANTO ASCII logo and tagline."""
    console = Console()
    console.print()

    # ── Logo ────────────────────────────────────────────────────────
    logo_text = Text(LOGO, style=BOLD_PRIMARY)
    console.print(logo_text)
    console.print()

    # Tagline
    tagline = Text()
    tagline.append("  Universal Memory Layer for Agentic AI\n", style="bold white")
    tagline.append("  powered by ", style="dim")
    tagline.append("moorcheh.ai", style=BOLD_PRIMARY)
    console.print(tagline)
    console.print()


def show_welcome_banner(config_manager: ConfigManager) -> None:
    """Render the full MEMANTO welcome banner to the console."""
    console = Console()

    # ── System ──────────────────────────────────────────────────────
    console.print(Rule("System", style=PRIMARY))
    py_ver = platform.python_version()
    os_name = platform.system()
    sys_line = Text()
    sys_line.append(f"  v{MEMANTO_VERSION}", style=BOLD_BRIGHT)
    sys_line.append("  ·  ", style="dim")
    sys_line.append(f"Python {py_ver}", style="white")
    sys_line.append("  ·  ", style="dim")
    sys_line.append(os_name, style="white")
    console.print(sys_line)
    console.print()

    # ── Status ──────────────────────────────────────────────────────
    console.print(Rule("Status", style=PRIMARY))

    has_key = config_manager.is_configured()
    config_manager.get_api_key()

    status_table = Table(show_header=False, box=None, padding=(0, 2), show_edge=False)
    status_table.add_column("Label", style="dim", min_width=14)
    status_table.add_column("Value")

    # API Key
    if has_key:
        status_table.add_row("  API Key", "[green]●[/green] configured")
    else:
        status_table.add_row("  API Key", "[red]●[/red] not configured")

    # Active Agent
    active_agent, _ = config_manager.get_active_session()
    if active_agent:
        status_table.add_row("  Agent", f"[green]●[/green] {active_agent} (active)")
    else:
        status_table.add_row("  Agent", "[dim]○[/dim] none")

    console.print(status_table)
    console.print()

    # ── Memory Types ────────────────────────────────────────────────
    console.print(Rule("Memory Types", style=PRIMARY))

    # Build 4-column rows of memory types
    cols = 4
    rows_text = []
    for i in range(0, len(MEMORY_TYPES), cols):
        chunk = MEMORY_TYPES[i : i + cols]
        row = Text("  ")
        for _j, mt in enumerate(chunk):
            row.append("◆ ", style=BOLD_PRIMARY)
            row.append(f"{mt:<14}", style="white")
        rows_text.append(row)

    for row in rows_text:
        console.print(row)
    console.print()

    # ── Quick Start ─────────────────────────────────────────────────
    console.print(Rule("Quick Start", style=PRIMARY))

    commands = [
        ("memanto status", "Full dashboard"),
        ("memanto agent create <agent_name_or_id>", "Create a new memanto agent"),
        ("memanto agent activate <agent_name_or_id>", "Begin a session"),
        ('memanto remember "..."', "Store a memory"),
        ('memanto recall "..."', "Search memories"),
        ('memanto answer "..."', "Ask a question (RAG)"),
        ("memanto connect list", "See agent integrations"),
        ("memanto connect <agent>", "Connect to an AI agent"),
        ("memanto serve", "Start API server"),
    ]

    cmd_table = Table(show_header=False, box=None, padding=(0, 1), show_edge=False)
    cmd_table.add_column("Cmd", style=BOLD_BRIGHT, min_width=28)
    cmd_table.add_column("Desc", style="dim")

    for cmd, desc in commands:
        cmd_table.add_row(f"  {cmd}", desc)

    console.print(cmd_table)
    console.print()

    # Note about server
    console.print("  [dim]Server is only needed for REST API endpoints.[/dim]")
    console.print(
        "  [dim]All CLI commands work directly without a running server.[/dim]"
    )
    console.print()

    # Footer
    console.print(
        f"  Run [{BOLD_PRIMARY}]memanto --help[/{BOLD_PRIMARY}] for all commands\n",
        style="dim",
    )
