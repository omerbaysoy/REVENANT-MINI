from __future__ import annotations

import hashlib
import logging
import os
import platform
import socket
from pathlib import Path
from typing import Any


STATE_DIR = Path.home() / ".revenant-mini"


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def platform_slug() -> str:
    system = platform.system().lower() or "unknown"
    machine = platform.machine().lower() or "unknown"
    if "ANDROID_ROOT" in os.environ or "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", ""):
        system = "termux"
    return "".join(ch if ch.isalnum() else "-" for ch in f"{system}-{machine}").strip("-")


def local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"


def stable_worker_id(configured_id: str | None = None) -> str:
    if configured_id:
        return configured_id
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / "worker_id"
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    seed = "|".join(
        [
            socket.gethostname(),
            platform.platform(),
            platform.machine(),
            str(Path.home()),
        ]
    )
    short_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    value = f"revenant-mini-{platform_slug()}-{short_hash}"
    path.write_text(value + "\n", encoding="utf-8")
    return value


def mqtt_client(client_id: str, **kwargs: Any):
    import paho.mqtt.client as mqtt

    if hasattr(mqtt, "CallbackAPIVersion"):
        return mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id=client_id,
            **kwargs,
        )
    return mqtt.Client(client_id=client_id, **kwargs)
