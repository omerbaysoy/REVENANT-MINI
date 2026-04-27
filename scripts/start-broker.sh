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

echo "Starting Mosquitto MQTT broker on 0.0.0.0:1883"
echo "Controller broker host: 127.0.0.1"
echo "Worker broker hint: ${LAN_IP}"
echo "Stop with Ctrl+C."
echo
exec mosquitto -p 1883 -v
