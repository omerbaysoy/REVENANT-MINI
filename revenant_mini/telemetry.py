from __future__ import annotations

import platform
import socket
import time
from pathlib import Path
from typing import Any

import psutil

from .utils import local_ip


BOOT_TIME = psutil.boot_time()


def temperature_c() -> float | None:
    thermal = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        raw = thermal.read_text(encoding="utf-8").strip()
        return round(float(raw) / 1000.0, 1)
    except (OSError, ValueError):
        return None


def collect(worker_id: str, status: str = "online") -> dict[str, Any]:
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "worker_id": worker_id,
        "hostname": socket.gethostname(),
        "OS": platform.system(),
        "kernel": platform.release(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "local IP": local_ip(),
        "CPU percent": psutil.cpu_percent(interval=None),
        "RAM total": ram.total,
        "RAM used": ram.used,
        "RAM percent": ram.percent,
        "disk total": disk.total,
        "disk used": disk.used,
        "disk percent": disk.percent,
        "temperature_c": temperature_c(),
        "uptime_seconds": int(time.time() - BOOT_TIME),
        "status": status,
        "timestamp": time.time(),
    }
