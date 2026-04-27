from __future__ import annotations

import platform
import shutil
import socket
import time
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

from .utils import local_ip


def _read_float(path: Path) -> float | None:
    try:
        return float(path.read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        return None


def _uptime_seconds() -> int | None:
    if psutil is not None:
        try:
            return int(time.time() - psutil.boot_time())
        except Exception:
            pass
    uptime = _read_float(Path("/proc/uptime"))
    return None if uptime is None else int(uptime)


def _meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw_value = line.split(":", 1)
            amount = raw_value.strip().split()[0]
            values[key] = int(amount) * 1024
    except (OSError, ValueError, IndexError):
        return {}
    return values


def _memory_stats() -> tuple[int | None, int | None, float | None]:
    if psutil is not None:
        try:
            ram = psutil.virtual_memory()
            return ram.total, ram.used, ram.percent
        except Exception:
            pass
    meminfo = _meminfo()
    total = meminfo.get("MemTotal")
    available = meminfo.get("MemAvailable")
    if total is None or available is None:
        return total, None, None
    used = max(total - available, 0)
    percent = round((used / total) * 100, 1) if total else None
    return total, used, percent


def _disk_stats() -> tuple[int | None, int | None, float | None]:
    try:
        disk = psutil.disk_usage("/") if psutil is not None else shutil.disk_usage(Path.home())
        return disk.total, disk.used, disk.percent
    except Exception:
        return None, None, None


def _cpu_percent() -> float | None:
    if psutil is None:
        return None
    try:
        return psutil.cpu_percent(interval=None)
    except Exception:
        return None


def temperature_c() -> float | None:
    thermal = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        raw = thermal.read_text(encoding="utf-8").strip()
        return round(float(raw) / 1000.0, 1)
    except (OSError, ValueError):
        return None


def collect(worker_id: str, status: str = "online") -> dict[str, Any]:
    ram_total, ram_used, ram_percent = _memory_stats()
    disk_total, disk_used, disk_percent = _disk_stats()
    return {
        "worker_id": worker_id,
        "hostname": _safe(socket.gethostname),
        "OS": _safe(platform.system),
        "kernel": _safe(platform.release),
        "platform": _safe(platform.platform),
        "architecture": _safe(platform.machine),
        "local IP": local_ip(),
        "CPU percent": _cpu_percent(),
        "RAM total": ram_total,
        "RAM used": ram_used,
        "RAM percent": ram_percent,
        "disk total": disk_total,
        "disk used": disk_used,
        "disk percent": disk_percent,
        "temperature_c": temperature_c(),
        "uptime_seconds": _uptime_seconds(),
        "status": status,
        "timestamp": time.time(),
    }


def _safe(func) -> str | None:
    try:
        return func()
    except Exception:
        return None
