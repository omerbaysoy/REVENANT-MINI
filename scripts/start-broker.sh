#!/usr/bin/env bash
set -euo pipefail

if ! command -v mosquitto >/dev/null 2>&1; then
  echo "mosquitto not found."
  echo "Install hint:"
  echo "  sudo apt update"
  echo "  sudo apt install -y mosquitto mosquitto-clients"
  exit 1
fi

LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
if [ -z "${LAN_IP}" ]; then
  LAN_IP="$(ip route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' || true)"
fi
if [ -z "${LAN_IP}" ]; then
  LAN_IP="127.0.0.1"
fi

listener_addresses() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltnH | awk '$4 ~ /:1883$/ {print $4}'
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn | awk '$4 ~ /:1883$/ {print $4}'
  fi
}

print_hints() {
  echo "Controller broker host: 127.0.0.1"
  echo "Worker broker hint: ${LAN_IP}"
  echo "Worker command: python -m revenant_mini worker --broker ${LAN_IP}"
}

LISTENERS="$(listener_addresses || true)"
if [ -n "${LISTENERS}" ]; then
  if echo "${LISTENERS}" | grep -Eq '(^|[:\[])(0\.0\.0\.0|\*|::)(\]|:)?1883$' || echo "${LISTENERS}" | grep -q "${LAN_IP}:1883"; then
    echo "MQTT broker already appears to be reachable for LAN workers on port 1883."
    print_hints
    exit 0
  fi
  if echo "${LISTENERS}" | grep -Eq '127\.0\.0\.1:1883|\[::1\]:1883|::1:1883'; then
    echo "Mosquitto is running but only bound to localhost. Remote workers cannot connect."
    echo "Run: sudo python -m revenant_mini broker-configure-lan"
    print_hints
    exit 0
  fi
  echo "Port 1883 is already in use, but LAN reachability could not be confirmed."
  echo "Detected listeners:"
  echo "${LISTENERS}"
  echo "Run: sudo python -m revenant_mini broker-configure-lan"
  exit 0
fi

echo "Starting Mosquitto MQTT broker on 0.0.0.0:1883"
print_hints
echo "Stop with Ctrl+C."
echo
exec mosquitto -p 1883 -v
