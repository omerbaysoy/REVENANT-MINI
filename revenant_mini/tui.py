from __future__ import annotations

from rich.console import Console
from rich.table import Table


console = Console()


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
            str(telemetry.get("hostname", "-")),
            str(telemetry.get("local IP", "-")),
            f"{telemetry.get('CPU percent', 0):.1f}%",
            f"{telemetry.get('RAM percent', 0):.1f}%",
            f"{telemetry.get('disk percent', 0):.1f}%",
            "-" if temp is None else f"{temp:.1f} C",
            f"{worker.get('last_seen_age', 0):.0f}s",
        )
    return table
