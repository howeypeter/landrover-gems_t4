"""Rich rendering helpers for the CLI — tables for live data and DTCs, actuator
outcomes, and the characterful "Communicating with ECU…" flavor.
"""
from __future__ import annotations

from rich.console import Console
from rich.table import Table

from gems_t4.gems.types import ActuatorOutcome, Dtc, Measure

console = Console()


def live_table(measures: list[Measure], *, title: str = "Live data") -> Table:
    """Build a table of live measures."""
    table = Table(title=title, header_style="bold cyan", expand=False)
    table.add_column("Parameter", style="white")
    table.add_column("Value", justify="right", style="green")
    table.add_column("Unit", style="dim")
    table.add_column("raw", justify="right", style="dim")
    for m in measures:
        val = f"{m.value:.2f}" if isinstance(m.value, float) else str(m.value)
        table.add_row(m.name, val, m.unit, f"0x{m.raw:X}")
    return table


def dtc_table(dtcs: list[Dtc], *, title: str = "Stored fault codes") -> Table:
    """Build a table of DTCs."""
    table = Table(title=title, header_style="bold yellow", expand=False)
    table.add_column("Code", style="bold red")
    table.add_column("State", style="magenta")
    table.add_column("Description", style="white")
    if not dtcs:
        table.add_row("-", "-", "No faults stored")
    for d in dtcs:
        table.add_row(d.code, d.state.value, d.description)
    return table


def print_live(measures: list[Measure], *, title: str = "Live data") -> None:
    console.print(live_table(measures, title=title))


def print_dtcs(dtcs: list[Dtc], *, title: str = "Stored fault codes") -> None:
    console.print(dtc_table(dtcs, title=title))


def print_actuator(outcome: ActuatorOutcome) -> None:
    style = "green" if outcome.ok else "bold red"
    mark = "OK" if outcome.ok else "REFUSED"
    console.print(f"[{style}]{mark}[/]: {outcome.message}")


def communicating(message: str = "Communicating with ECU... please wait") -> None:
    """Print the authentic slow-tool status line."""
    console.print(f"[dim italic]{message}[/]")
