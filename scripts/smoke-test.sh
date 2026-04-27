#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
PYTHON_BIN="${PYTHON:-python3}"

"${PYTHON_BIN}" - <<'PY'
import revenant_mini
import revenant_mini.cli
import revenant_mini.controller
import revenant_mini.worker
print("imports ok", revenant_mini.__version__)
PY

"${PYTHON_BIN}" -m revenant_mini --help >/dev/null
"${PYTHON_BIN}" -m revenant_mini doctor
bash install/install.sh --help >/dev/null

for path in \
  requirements.txt pyproject.toml README.md LICENSE .gitignore \
  revenant_mini/__init__.py revenant_mini/__main__.py revenant_mini/cli.py \
  revenant_mini/controller.py revenant_mini/worker.py revenant_mini/broker.py \
  revenant_mini/telemetry.py revenant_mini/protocol.py revenant_mini/topics.py \
  revenant_mini/tui.py revenant_mini/banner.py revenant_mini/utils.py \
  install/install.sh install/install-termux.sh \
  configs/controller.example.toml configs/worker.example.toml scripts/start-broker.sh
do
  test -f "${path}" || { echo "missing ${path}"; exit 1; }
done

echo "smoke test ok"
