from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

PORT = 1883
MOSQUITTO_LAN_CONFIG = Path("/etc/mosquitto/conf.d/revenant-mini.conf")
MOSQUITTO_LAN_CONTENT = "listener 1883 0.0.0.0\nallow_anonymous true\n"


def local_ips() -> list[str]:
    ips = {"127.0.0.1", "::1"}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ips.add(sock.getsockname()[0])
    except OSError:
        pass
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            address = info[4][0]
            if address:
                ips.add(address)
    except OSError:
        pass
    return sorted(ips)


def lan_ip() -> str:
    for ip in local_ips():
        if not ip.startswith("127.") and ip != "::1":
            return ip
    return "127.0.0.1"


def _run_capture(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return ""
    return completed.stdout


def _parse_listener_address(line: str) -> str | None:
    parts = line.split()
    for part in parts:
        if part.endswith(f":{PORT}") or part.endswith(f".{PORT}") or f":{PORT}]" in part:
            address = part.rsplit(":", 1)[0]
            return address.strip("[]")
    return None


def port_listeners(port: int = PORT) -> list[str]:
    output = _run_capture(["ss", "-ltnH"])
    if not output:
        output = _run_capture(["netstat", "-ltn"])
    listeners: list[str] = []
    for line in output.splitlines():
        if f":{port}" not in line and f".{port}" not in line:
            continue
        address = _parse_listener_address(line)
        if address:
            listeners.append(address)
    return listeners


def is_lan_reachable_listener(address: str, known_ips: set[str]) -> bool:
    return address in {"0.0.0.0", "*", "::", ""} or address in {
        ip for ip in known_ips if not ip.startswith("127.") and ip != "::1"
    }


def listener_status(port: int = PORT) -> str:
    listeners = port_listeners(port)
    if not listeners:
        return "free"
    known_ips = set(local_ips())
    if any(is_lan_reachable_listener(address, known_ips) for address in listeners):
        return "lan"
    if all(address.startswith("127.") or address == "::1" for address in listeners):
        return "localhost"
    return "localhost"


def print_broker_hints() -> None:
    worker_host = lan_ip()
    print("Controller broker host: 127.0.0.1")
    print(f"Worker broker hint: {worker_host}")
    print(f"Worker command: python -m revenant_mini worker --broker {worker_host}")


def start_broker() -> int:
    status = listener_status()
    if status == "lan":
        print("MQTT broker already appears to be reachable for LAN workers on port 1883.")
        print_broker_hints()
        return 0
    if status == "localhost":
        print("Mosquitto is running but only bound to localhost. Remote workers cannot connect.")
        print("Run: sudo python -m revenant_mini broker-configure-lan")
        print_broker_hints()
        return 0

    script = Path(__file__).resolve().parent.parent / "scripts" / "start-broker.sh"
    if script.exists():
        return subprocess.call(["bash", str(script)])
    if not shutil.which("mosquitto"):
        print("mosquitto not found. Install with: sudo apt update && sudo apt install -y mosquitto mosquitto-clients")
        return 1
    print("Starting Mosquitto MQTT broker on 0.0.0.0:1883")
    print_broker_hints()
    return subprocess.call(["mosquitto", "-p", "1883", "-v"])


def configure_lan_broker() -> int:
    if os.geteuid() != 0:
        print("This command must be run with sudo:")
        print("sudo python -m revenant_mini broker-configure-lan")
        return 1
    if not shutil.which("mosquitto"):
        print("mosquitto not found. Install with: sudo apt update && sudo apt install -y mosquitto mosquitto-clients")
        return 1
    if not shutil.which("systemctl"):
        print("systemctl not found. Restart Mosquitto manually after writing the LAN configuration.")
        return 1

    MOSQUITTO_LAN_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if MOSQUITTO_LAN_CONFIG.exists():
        backup = MOSQUITTO_LAN_CONFIG.with_suffix(MOSQUITTO_LAN_CONFIG.suffix + f".bak.{time.strftime('%Y%m%d%H%M%S')}")
        shutil.copy2(MOSQUITTO_LAN_CONFIG, backup)
        print(f"Backed up existing config to {backup}")
    MOSQUITTO_LAN_CONFIG.write_text(MOSQUITTO_LAN_CONTENT, encoding="utf-8")
    print(f"Wrote {MOSQUITTO_LAN_CONFIG}")

    restarted = subprocess.run(["systemctl", "restart", "mosquitto"], check=False)
    if restarted.returncode != 0:
        print("Failed to restart Mosquitto with systemctl restart mosquitto.")
        return restarted.returncode or 1

    time.sleep(0.5)
    status = listener_status()
    if status == "lan":
        print("Mosquitto is now listening for LAN workers on port 1883.")
        print_broker_hints()
        return 0
    listeners = ", ".join(port_listeners()) or "none"
    print("Mosquitto restarted, but port 1883 does not appear to be LAN-reachable.")
    print(f"Detected listeners: {listeners}")
    print("Check Mosquitto logs with: sudo journalctl -u mosquitto -n 50 --no-pager")
    return 1
