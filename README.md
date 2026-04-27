# REVENANT-MINI

░█▀▄░█▀▀░█░█░█▀▀░█▀█░█▀█░█▀█░▀█▀░░░░░█▄█░▀█▀░█▀█░▀█▀
░█▀▄░█▀▀░▀▄▀░█▀▀░█░█░█▀█░█░█░░█░░▄▄▄░█░█░░█░░█░█░░█░
░▀░▀░▀▀▀░░▀░░▀▀▀░▀░▀░▀░▀░▀░▀░░▀░░░░░░▀░▀░▀▀▀░▀░▀░▀▀▀

REVENANT-MINI is a local-first mini swarm controller for a controller/main machine and multiple local-network workers. The controller runs a local Mosquitto MQTT broker; workers connect to it, send telemetry and heartbeats, receive broadcast commands, execute them locally, and publish command results.

Supported platforms:

- Linux
- Raspberry Pi / Raspberry Pi OS
- Android Termux, rooted or unrooted, as worker only

Architecture:

```text
controller machine -> local Mosquitto broker -> Linux/Raspberry Pi/Termux workers
```

MQTT topic prefix: `revenant-mini/v1`

## One-Liners

Controller:

```bash
curl -sSL https://raw.githubusercontent.com/omerbaysoy/REVENANT-MINI/main/install/install.sh | bash -s -- --mode controller
```

Worker:

```bash
curl -sSL https://raw.githubusercontent.com/omerbaysoy/REVENANT-MINI/main/install/install.sh | bash -s -- --mode worker --broker <CONTROLLER_IP>
```

Termux worker:

```bash
curl -sSL https://raw.githubusercontent.com/omerbaysoy/REVENANT-MINI/main/install/install.sh | bash -s -- --mode worker --broker <CONTROLLER_IP>
```

## Manual Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install Mosquitto on the controller:

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
```

Start the broker:

```bash
python -m revenant_mini broker-start
```

Start the controller:

```bash
python -m revenant_mini controller
```

Start a worker:

```bash
python -m revenant_mini worker --broker <BROKER_IP>
```

Broadcast a command:

```bash
python -m revenant_mini send --all "uname -a"
python -m revenant_mini send --all "apt update"
```

The running controller shows worker telemetry, online/stale/offline status, and command results.

## CLI

```bash
python -m revenant_mini --help
python -m revenant_mini doctor
python -m revenant_mini broker-start
python -m revenant_mini controller
python -m revenant_mini worker --broker <BROKER_IP>
python -m revenant_mini nodes
python -m revenant_mini send --all "uname -a"
```

## Installer Behavior

`install/install.sh` detects Termux, Raspberry Pi OS, Debian/Ubuntu Linux, architecture, and the available package tool. It uses `pkg` on Termux and `apt` on Debian/Ubuntu/Raspberry Pi OS. Controller mode installs `mosquitto` and `mosquitto-clients`; worker mode does not install broker packages. Termux controller mode exits with a clear unsupported message.

The installer clones or updates the repo into `~/.revenant-mini/src`, creates a venv under `~/.revenant-mini/venv` where supported, installs requirements, writes config into `~/.revenant-mini/config/`, backs up existing config before overwrite, and prints final run commands.

## Troubleshooting

Broker connection refused:

- Start the broker on the controller with `python -m revenant_mini broker-start`.
- Check that port `1883` is reachable from the worker.

Wrong broker IP:

- Use the controller LAN IP, not `127.0.0.1`, when starting workers on other devices.
- `scripts/start-broker.sh` prints a LAN IP hint.

Local worker works but Raspberry Pi / Termux worker cannot connect:

- Cause: Mosquitto may be bound only to `127.0.0.1`, so remote LAN devices cannot reach it.
- Fix:

```bash
sudo python -m revenant_mini broker-configure-lan
```

- Verify:

```bash
sudo ss -ltnp | grep 1883
```

- Expected listener:

```text
0.0.0.0:1883
```

Mosquitto missing:

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
```

Termux limitations:

- Termux is supported as a worker.
- Termux controller mode is intentionally unsupported in this MVP.
- Some system telemetry may be unavailable without extra Android permissions.

Temperature is null:

- This is expected when `/sys/class/thermal/thermal_zone0/temp` is unavailable or inaccessible.
- REVENANT-MINI never crashes when temperature cannot be read.

Unsupported distro/package tool:

- The installer supports Termux `pkg` and Debian/Ubuntu/Raspberry Pi OS `apt`.
- On other systems, install Python 3.10+, dependencies from `requirements.txt`, and Mosquitto manually.
