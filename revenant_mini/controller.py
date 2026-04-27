from __future__ import annotations

import logging
import time
from typing import Any

from rich.live import Live
from rich.panel import Panel

from . import protocol, topics
from .banner import BANNER
from .tui import console, worker_table
from .utils import mqtt_client

LOG = logging.getLogger(__name__)


class Controller:
    def __init__(self, broker_host: str = "127.0.0.1", broker_port: int = 1883, refresh_seconds: int = 2) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.refresh_seconds = refresh_seconds
        self.workers: dict[str, dict[str, Any]] = {}
        self.client = mqtt_client("revenant-mini-controller")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(min_delay=2, max_delay=30)

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            LOG.warning("MQTT connect failed with rc=%s", rc)
            return
        client.subscribe(topics.workers_wildcard(), qos=1)
        console.log(f"[green]connected[/green] to broker {self.broker_host}:{self.broker_port}")

    def _on_message(self, client, userdata, msg):
        try:
            data = protocol.loads(msg.payload)
        except Exception as exc:
            LOG.warning("invalid message on %s: %s", msg.topic, exc)
            return
        parts = msg.topic.split("/")
        if len(parts) < 5:
            return
        worker_id = parts[3]
        topic_type = parts[4]
        worker = self.workers.setdefault(worker_id, {"status": "unknown", "last_seen": time.time()})
        worker["last_seen"] = time.time()
        payload = data.get("payload", {})
        if topic_type in {"hello", "telemetry"}:
            worker["telemetry"] = payload
            worker["status"] = payload.get("status", worker.get("status", "online"))
        elif topic_type == "status":
            worker["status"] = payload.get("status", "unknown")
        elif topic_type == "heartbeat":
            worker["status"] = payload.get("status", "online")
        elif topic_type == "result":
            worker["last_result"] = payload
            command_id = payload.get("command_id", "-")
            rc = payload.get("returncode")
            console.print(
                Panel.fit(
                    f"[white]{worker_id}[/white]\ncommand_id: [cyan]{command_id}[/cyan]\nreturncode: {rc}\nduration: {payload.get('duration_seconds')}s\n\n[green]stdout[/green]\n{payload.get('stdout') or ''}\n[red]stderr[/red]\n{payload.get('stderr') or ''}",
                    title="Command Result",
                    border_style="red",
                )
            )

    def render(self):
        now = time.time()
        for worker in self.workers.values():
            worker["last_seen_age"] = now - worker.get("last_seen", now)
            if worker["last_seen_age"] > 20 and worker.get("status") == "online":
                worker["status"] = "stale"
        return worker_table(self.workers)

    def run(self) -> None:
        console.print(f"[red]{BANNER}[/red]")
        self.client.connect(self.broker_host, self.broker_port, keepalive=30)
        self.client.loop_start()
        try:
            with Live(self.render(), console=console, refresh_per_second=1 / max(self.refresh_seconds, 1), screen=False) as live:
                while True:
                    live.update(self.render())
                    time.sleep(self.refresh_seconds)
        except KeyboardInterrupt:
            console.print("[yellow]controller stopping[/yellow]")
        finally:
            self.client.disconnect()
            self.client.loop_stop()
