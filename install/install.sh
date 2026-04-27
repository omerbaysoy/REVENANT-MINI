#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/omerbaysoy/REVENANT-MINI.git"
BASE_DIR="${HOME}/.revenant-mini"
SRC_DIR="${BASE_DIR}/src"
VENV_DIR="${BASE_DIR}/venv"
CONFIG_DIR="${BASE_DIR}/config"
MODE=""
BROKER=""

usage() {
  cat <<'EOF'
REVENANT-MINI installer

Usage:
  install.sh --mode controller
  install.sh --mode worker --broker <BROKER_IP>

Options:
  --mode controller|worker  Install controller or worker runtime.
  --broker HOST            Required for worker mode.
  --help                   Show this help.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --broker)
      BROKER="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [ "${MODE}" != "controller" ] && [ "${MODE}" != "worker" ]; then
  echo "--mode must be controller or worker" >&2
  exit 2
fi
if [ "${MODE}" = "worker" ] && [ -z "${BROKER}" ]; then
  echo "--broker is required for worker mode" >&2
  exit 2
fi

IS_TERMUX=0
IS_RPI=0
OS_NAME="$(uname -s)"
ARCH="$(uname -m)"
PKG_MANAGER=""

if [ -n "${PREFIX:-}" ] && echo "${PREFIX}" | grep -q "com.termux"; then
  IS_TERMUX=1
  PKG_MANAGER="pkg"
elif [ -f /proc/device-tree/model ] && tr -d '\0' </proc/device-tree/model | grep -qi "raspberry pi"; then
  IS_RPI=1
  PKG_MANAGER="apt"
elif command -v apt >/dev/null 2>&1; then
  PKG_MANAGER="apt"
else
  echo "Unsupported distro/package manager. This installer supports Termux pkg and Debian/Ubuntu/Raspberry Pi apt." >&2
  exit 1
fi

if [ "${IS_TERMUX}" -eq 1 ] && [ "${MODE}" = "controller" ]; then
  echo "Termux controller mode is unsupported. Use Termux as a worker and run the controller on Linux/Raspberry Pi OS." >&2
  exit 1
fi

echo "Detected platform:"
echo "  os: ${OS_NAME}"
echo "  architecture: ${ARCH}"
echo "  package_manager: ${PKG_MANAGER}"
echo "  termux: ${IS_TERMUX}"
echo "  raspberry_pi: ${IS_RPI}"
echo "  mode: ${MODE}"

if [ "${PKG_MANAGER}" = "pkg" ]; then
  pkg update
  pkg install -y git python
elif [ "${PKG_MANAGER}" = "apt" ]; then
  sudo apt update
  sudo apt install -y git python3 python3-venv python3-pip
  if [ "${MODE}" = "controller" ]; then
    sudo apt install -y mosquitto mosquitto-clients
  fi
fi

mkdir -p "${BASE_DIR}" "${CONFIG_DIR}"
if [ -d "${SRC_DIR}/.git" ]; then
  git -C "${SRC_DIR}" pull --ff-only
else
  rm -rf "${SRC_DIR}"
  git clone "${REPO_URL}" "${SRC_DIR}"
fi

PYTHON_BIN="python3"
if [ "${IS_TERMUX}" -eq 1 ]; then
  PYTHON_BIN="python"
fi

if "${PYTHON_BIN}" -m venv "${VENV_DIR}"; then
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip
  "${VENV_DIR}/bin/python" -m pip install -r "${SRC_DIR}/requirements.txt"
  RUN_PY="${VENV_DIR}/bin/python"
else
  echo "Virtualenv creation failed; falling back to user install." >&2
  "${PYTHON_BIN}" -m pip install --user -r "${SRC_DIR}/requirements.txt"
  RUN_PY="${PYTHON_BIN}"
fi

backup_if_exists() {
  local path="$1"
  if [ -f "${path}" ]; then
    cp "${path}" "${path}.bak.$(date +%Y%m%d%H%M%S)"
  fi
}

if [ "${MODE}" = "controller" ]; then
  CONFIG_PATH="${CONFIG_DIR}/controller.toml"
  backup_if_exists "${CONFIG_PATH}"
  cp "${SRC_DIR}/configs/controller.example.toml" "${CONFIG_PATH}"
else
  CONFIG_PATH="${CONFIG_DIR}/worker.toml"
  backup_if_exists "${CONFIG_PATH}"
  sed "s/host = \"127.0.0.1\"/host = \"${BROKER}\"/" "${SRC_DIR}/configs/worker.example.toml" >"${CONFIG_PATH}"
fi

echo
echo "Install complete."
echo "Source: ${SRC_DIR}"
echo "Config: ${CONFIG_PATH}"
echo
echo "Final run commands:"
if [ "${MODE}" = "controller" ]; then
  echo "  ${RUN_PY} -m revenant_mini broker-start"
  echo "  ${RUN_PY} -m revenant_mini controller"
else
  echo "  ${RUN_PY} -m revenant_mini worker --broker ${BROKER}"
fi
