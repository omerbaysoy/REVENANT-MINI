from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def start_broker() -> int:
    script = Path(__file__).resolve().parent.parent / "scripts" / "start-broker.sh"
    if script.exists():
        return subprocess.call(["bash", str(script)])
    if not shutil.which("mosquitto"):
        print("mosquitto not found. Install with: sudo apt update && sudo apt install -y mosquitto mosquitto-clients")
        return 1
    return subprocess.call(["mosquitto", "-p", "1883", "-v"])
