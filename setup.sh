#!/usr/bin/env bash
# Run as your normal user on an Orange Pi Zero 2W with Debian 12.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [ "$(id -u)" -eq 0 ]; then
    echo "Run bash setup.sh without sudo; it requests sudo when needed." >&2
    exit 1
fi
if ! command -v apt-get >/dev/null; then
    echo "This setup requires Debian with apt-get (tested target: Debian 12)." >&2
    exit 1
fi
if systemctl is-active --quiet kiln-controller; then
    echo "The controller is running. Wait until the kiln is idle, then follow docs/INSTALL.md to stop it before setup." >&2
    exit 1
fi

sudo apt-get update
sudo apt-get install -y git ca-certificates build-essential python3-dev python3-venv \
    python3-libgpiod gpiod libgpiod-dev chrony avahi-daemon curl
sudo systemctl enable --now chrony avahi-daemon

getent group gpio >/dev/null || sudo groupadd --system gpio
sudo usermod -aG gpio "$(id -un)"
printf '%s\n' 'SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"' \
    | sudo tee /etc/udev/rules.d/60-kiln-gpio.rules >/dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=gpio

python3 -m venv --system-site-packages venv
venv/bin/python -m pip install --upgrade pip
kiln_requirements="$(mktemp)"
trap 'rm -f "$kiln_requirements"' EXIT
sed '/^[[:space:]]*RPi\.GPIO[[:space:]]*$/d' requirements.txt > "$kiln_requirements"
venv/bin/python -m pip install -r "$kiln_requirements" 'Adafruit-Blinka==9.2.0' pytest
venv/bin/python -m pip check

printf '\n%s\n' \
    'Setup complete. Log out and reconnect to activate GPIO group membership.' \
    'Next: follow docs/INSTALL.md from step 4 for simulation and commissioning.' \
    'The kiln controller has not been started; existing settings and firing data are unchanged.'
