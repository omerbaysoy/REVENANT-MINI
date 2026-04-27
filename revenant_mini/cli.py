from __future__ import annotations

import argparse
import importlib
import shutil
import sys

from rich.console import Console

from . import __version__, protocol, topics
from .banner import BANNER
from .broker import start_broker
from .controller import Controller
from .utils import mqtt_client, setup_logging
from .worker import Worker

console = Console()


def doctor(args: argparse.Namespace) -> int:
    console.print(f"[red]{BANNER}[/red]")
    console.print(f"REVENANT-MINI [white]{__version__}[/white]")
    ok = True
    for module in ("paho.mqtt.client", "psutil", "rich"):
        try:
            importlib.import_module(module)
            found = True
        except ImportError:
            found = False
        ok = ok and found
        console.print(f"{module}: {'[green]ok[/green]' if found else '[red]missing[/red]'}")
    mosquitto = shutil.which("mosquitto")
    console.print(f"mosquitto: {'[green]' + mosquitto + '[/green]' if mosquitto else '[yellow]missing[/yellow]'}")
    if not mosquitto:
        console.print("[yellow]Install hint:[/yellow] sudo apt update && sudo apt install -y mosquitto mosquitto-clients")
    return 0 if ok else 1


def send_command(args: argparse.Namespace) -> int:
    if not args.all:
        console.print("[red]Only --all broadcast is supported in this MVP.[/red]")
        return 2
    command_id = protocol.command_id()
    payload = {
        "command_id": command_id,
        "command": args.command,
        "timestamp": protocol.now(),
        "timeout_seconds": args.timeout,
    }
    topic = topics.commands_all()
    client = mqtt_client(f"revenant-mini-send-{command_id}")
    client.connect(args.broker, args.port, keepalive=30)
    client.loop_start()
    info = client.publish(topic, protocol.dumps(protocol.message("command", payload)), qos=1)
    info.wait_for_publish(timeout=5)
    client.disconnect()
    client.loop_stop()
    console.print(f"command_id: [cyan]{command_id}[/cyan]")
    console.print(f"topic: [white]{topic}[/white]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="revenant-mini", description="Local-first mini swarm controller.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    parser.add_argument("--version", action="version", version=f"revenant-mini {__version__}")
    sub = parser.add_subparsers(dest="command_name")

    sub.add_parser("doctor", help="Check local runtime dependencies.").set_defaults(func=doctor)
    sub.add_parser("broker-start", help="Start local Mosquitto broker on port 1883.").set_defaults(func=lambda args: start_broker())

    controller = sub.add_parser("controller", help="Run the controller TUI.")
    controller.add_argument("--broker", default="127.0.0.1", help="MQTT broker host.")
    controller.add_argument("--port", type=int, default=1883, help="MQTT broker port.")
    controller.add_argument("--refresh", type=int, default=2, help="Refresh interval in seconds.")
    controller.set_defaults(func=lambda args: Controller(args.broker, args.port, args.refresh).run() or 0)

    worker = sub.add_parser("worker", help="Run a worker.")
    worker.add_argument("--broker", required=True, help="MQTT broker host/IP.")
    worker.add_argument("--port", type=int, default=1883, help="MQTT broker port.")
    worker.add_argument("--id", default="", help="Optional stable worker id override.")
    worker.add_argument("--telemetry-interval", type=int, default=10, help="Telemetry interval in seconds.")
    worker.add_argument("--heartbeat-interval", type=int, default=5, help="Heartbeat interval in seconds.")
    worker.add_argument("--command-timeout", type=int, default=300, help="Command timeout in seconds.")
    worker.set_defaults(
        func=lambda args: Worker(
            args.broker,
            args.port,
            args.id,
            args.telemetry_interval,
            args.heartbeat_interval,
            args.command_timeout,
        ).run()
        or 0
    )

    sub.add_parser("nodes", help="Run the controller view of known nodes.").set_defaults(
        func=lambda args: Controller("127.0.0.1", 1883, 2).run() or 0
    )

    sender = sub.add_parser("send", help="Broadcast a command.")
    sender.add_argument("--broker", default="127.0.0.1", help="MQTT broker host.")
    sender.add_argument("--port", type=int, default=1883, help="MQTT broker port.")
    sender.add_argument("--timeout", type=int, default=300, help="Worker command timeout in seconds.")
    sender.add_argument("--all", action="store_true", help="Send to every worker.")
    sender.add_argument("command", help="Shell command to execute.")
    sender.set_defaults(func=send_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        console.print("[yellow]interrupted[/yellow]")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
