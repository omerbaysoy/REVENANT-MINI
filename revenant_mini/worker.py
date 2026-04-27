from __future__ import annotations

import logging
import subprocess
import threading
import time
from typing import Any

from . import protocol, telemetry, topics
from .utils import mqtt_client, stable_worker_id

LOG = logging.getLogger(__name__)
BACKOFF_SECONDS = [2, 5, 10, 20, 30]


class Worker:
    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        worker_id: str | None = None,
        telemetry_interval: int = 10,
        heartbeat_interval: int = 5,
        command_timeout: int = 300,
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.worker_id = stable_worker_id(worker_id)
        self.telemetry_interval = telemetry_interval
        self.heartbeat_interval = heartbeat_interval
        self.command_timeout = command_timeout
        self.stop_event = threading.Event()
        self.connected = threading.Event()
        self.seen_commands: set[str] = set()
        self.client = mqtt_client(f"{self.worker_id}-client")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(min_delay=2, max_delay=30)

    def _publish(self, topic: str, data: dict[str, Any], retain: bool = False) -> None:
        self.client.publish(topic, protocol.dumps(data), qos=1, retain=retain)

    def publish_online(self) -> None:
        self._publish(topics.hello(self.worker_id), protocol.message("hello", telemetry.collect(self.worker_id), self.worker_id))
        self._publish(topics.status(self.worker_id), protocol.message("status", {"status": "online"}, self.worker_id), retain=True)

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            LOG.warning("MQTT connect failed with rc=%s", rc)
            return
        LOG.info("connected to broker %s:%s as %s", self.broker_host, self.broker_port, self.worker_id)
        self.connected.set()
        client.subscribe([(topics.commands_all(), 1), (topics.command(self.worker_id), 1)])
        self.publish_online()

    def _on_disconnect(self, client, userdata, rc):
        self.connected.clear()
        if not self.stop_event.is_set():
            LOG.warning("disconnected from broker rc=%s; paho will reconnect", rc)

    def _on_message(self, client, userdata, msg):
        try:
            data = protocol.loads(msg.payload)
            payload = data.get("payload", {})
            command_id = payload.get("command_id") or data.get("command_id")
            command = payload.get("command") or data.get("command")
            timeout = int(payload.get("timeout_seconds") or self.command_timeout)
        except Exception as exc:
            LOG.warning("invalid command message on %s: %s", msg.topic, exc)
            return
        if not command:
            return
        if command_id in self.seen_commands:
            return
        if command_id:
            self.seen_commands.add(command_id)
        threading.Thread(target=self._execute_and_publish, args=(command_id, command, timeout), daemon=True).start()

    def _execute_and_publish(self, command_id: str | None, command: str, timeout: int) -> None:
        started = time.monotonic()
        result: dict[str, Any] = {
            "command_id": command_id,
            "command": command,
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "duration_seconds": 0.0,
            "timed_out": False,
        }
        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            result.update(
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            result.update(
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\ncommand timed out after {timeout}s",
                returncode=124,
                timed_out=True,
            )
        except Exception as exc:
            result.update(stderr=str(exc), returncode=1)
        result["duration_seconds"] = round(time.monotonic() - started, 3)
        self._publish(topics.result(self.worker_id), protocol.message("result", result, self.worker_id))

    def _periodic(self, interval: int, publish_func) -> None:
        while not self.stop_event.wait(interval):
            if self.connected.is_set():
                publish_func()

    def run(self) -> None:
        self.client.loop_start()
        backoff_index = 0
        heartbeat_thread = threading.Thread(target=self._periodic, args=(self.heartbeat_interval, self.publish_heartbeat), daemon=True)
        telemetry_thread = threading.Thread(target=self._periodic, args=(self.telemetry_interval, self.publish_telemetry), daemon=True)
        heartbeat_thread.start()
        telemetry_thread.start()
        try:
            while not self.stop_event.is_set():
                if not self.connected.is_set():
                    delay = BACKOFF_SECONDS[min(backoff_index, len(BACKOFF_SECONDS) - 1)]
                    try:
                        LOG.info("connecting to broker %s:%s", self.broker_host, self.broker_port)
                        self.client.connect(self.broker_host, self.broker_port, keepalive=30)
                        backoff_index = 0
                    except OSError as exc:
                        LOG.warning("connect failed: %s; retrying in %ss", exc, delay)
                        backoff_index += 1
                        self.stop_event.wait(delay)
                        continue
                self.stop_event.wait(1)
        except KeyboardInterrupt:
            LOG.info("stopping worker")
        finally:
            self.stop()

    def publish_heartbeat(self) -> None:
        self._publish(topics.heartbeat(self.worker_id), protocol.message("heartbeat", {"status": "online"}, self.worker_id))

    def publish_telemetry(self) -> None:
        self._publish(topics.telemetry(self.worker_id), protocol.message("telemetry", telemetry.collect(self.worker_id), self.worker_id))

    def stop(self) -> None:
        self.stop_event.set()
        try:
            if self.connected.is_set():
                self._publish(topics.status(self.worker_id), protocol.message("status", {"status": "offline"}, self.worker_id), retain=True)
                time.sleep(0.2)
            self.client.disconnect()
        finally:
            self.client.loop_stop()
