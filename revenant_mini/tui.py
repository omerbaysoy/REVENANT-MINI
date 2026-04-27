from __future__ import annotations

from rich.console import Console
from rich.table import Table


console = Console()


def _percent(value) -> str:
    return "-" if value is None else f"{value:.1f}%"


def _text(value) -> str:
    return "-" if value is None else str(value)


def worker_table(workers: dict[str, dict]) -> Table:
    table = Table(title="REVENANT-MINI Workers", border_style="red")
    table.add_column("Worker", style="white", no_wrap=True)
    table.add_column("Status")
    table.add_column("Host", style="bright_white")
    table.add_column("IP", style="cyan")
    table.add_column("CPU", justify="right")
    table.add_column("RAM", justify="right")
    table.add_column("Disk", justify="right")
    table.add_column("Temp", justify="right")
    table.add_column("Last Seen", justify="right")
    for worker_id, worker in sorted(workers.items()):
        telemetry = worker.get("telemetry", {})
        status = worker.get("status", "unknown")
        style = "green" if status == "online" else "red" if status == "offline" else "yellow"
        temp = telemetry.get("temperature_c")
        table.add_row(
            worker_id,
            f"[{style}]{status}[/{style}]",
            _text(telemetry.get("hostname")),
            _text(telemetry.get("local IP")),
            _percent(telemetry.get("CPU percent")),
            _percent(telemetry.get("RAM percent")),
            _percent(telemetry.get("disk percent")),
            "-" if temp is None else f"{temp:.1f} C",
            f"{worker.get('last_seen_age', 0):.0f}s",
        )
    return table
