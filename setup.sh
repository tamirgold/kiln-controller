#!/usr/bin/env bash
# Install as your normal user; hardware is selected explicitly.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

usage() {
    cat <<'EOF'
Usage: bash setup.sh [--board BOARD] [--skip-system] [--dry-run]

BOARD is simulation (default), raspberry-pi, or orange-pi-zero-2w.
  simulation         Install the browser/controller preview without GPIO packages.
  raspberry-pi       Raspberry Pi 3/4, Raspberry Pi OS Bookworm, 40-pin header.
  orange-pi-zero-2w  Orange Pi Zero 2W, Debian 12, recorded working GPIO stack.

--skip-system  Skip apt, groups and udev; use preinstalled OS dependencies.
--dry-run      Print the installation steps without changing anything.
--help         Show this help.

Run without sudo. No controller service is installed, enabled, or started.
New settings start in simulation with automatic recovery disabled. Existing
settings, programs, and firing records are preserved. Hardware still requires
the matching build guide linked from docs/GETTING-STARTED.md.
EOF
}

kiln_board=simulation
kiln_skip_system=0
kiln_dry_run=0
while (($#)); do
    case "$1" in
        --board)
            if (($# < 2)); then echo '--board needs a value.' >&2; exit 2; fi
            kiln_board=$2; shift 2 ;;
        --skip-system) kiln_skip_system=1; shift ;;
        --dry-run) kiln_dry_run=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

case "$kiln_board" in
    simulation)
        kiln_requirements=requirements.txt
        kiln_next='bash scripts/run-simulation.sh'
        kiln_guide=docs/GETTING-STARTED.md
        kiln_address=http://localhost:8081/picoreflow/index.html ;;
    raspberry-pi)
        kiln_requirements=requirements-raspberry-pi.txt
        kiln_next='KILN_BOARD=raspberry-pi bash scripts/run-simulation.sh'
        kiln_guide=docs/builds/raspberry-pi.md
        kiln_address='http://<your-board-hostname-or-IP>:8081/picoreflow/index.html' ;;
    orange-pi-zero-2w)
        kiln_requirements=requirements-hardware.txt
        kiln_next='KILN_BOARD=orange-pi-zero-2w bash scripts/run-simulation.sh'
        kiln_guide=docs/INSTALL.md
        kiln_address='http://<your-board-hostname-or-IP>:8081/picoreflow/index.html' ;;
    *) echo "Unsupported board: $kiln_board. Use --help for choices." >&2; exit 2 ;;
esac

# Parse first so --help and --dry-run work without an apt-based hardware host.
if (( ! kiln_dry_run )); then
    if [ "$(id -u)" -eq 0 ]; then
        echo 'Run bash setup.sh without sudo; it requests sudo when needed.' >&2
        exit 1
    fi
    if [ "$(uname -s)" != Linux ]; then
        echo 'Run setup on Linux (the Pi itself, or Linux/WSL for simulation).' >&2
        exit 1
    fi
    if (( ! kiln_skip_system )) && ! command -v apt-get >/dev/null; then
        echo 'This setup needs Debian/Raspberry Pi OS with apt-get, or --skip-system.' >&2
        exit 1
    fi
    if command -v systemctl >/dev/null && systemctl is-active --quiet kiln-controller; then
        echo 'The controller is running. Wait until the kiln is idle, then follow docs/MAINTENANCE.md before updating.' >&2
        exit 1
    fi
    if [ "$kiln_board" != simulation ]; then
        python3 - "$kiln_board" <<'PY'
import sys
from lib.board_profiles import BoardConfigurationError, detected_model, get_profile
try:
    get_profile(sys.argv[1]).validate_model(detected_model())
except BoardConfigurationError as error:
    print(error, file=sys.stderr)
    sys.exit(1)
PY
    fi
fi

run() {
    if (( kiln_dry_run )); then
        printf '  '; printf '%q ' "$@"; printf '\n'
    else
        "$@"
    fi
}

printf 'Installing for %s\n' "$kiln_board"
if (( kiln_dry_run )); then echo '(Preview only: no changes will be made.)'; fi
if (( ! kiln_skip_system )); then
    kiln_packages=(git ca-certificates build-essential python3-dev python3-venv curl)
    if [ "$kiln_board" != simulation ]; then
        kiln_packages+=(python3-libgpiod gpiod libgpiod-dev chrony avahi-daemon)
    fi
    run sudo apt-get update
    run sudo apt-get install -y "${kiln_packages[@]}"
    if [ "$kiln_board" != simulation ]; then
        run sudo systemctl enable --now chrony avahi-daemon
        if ! getent group gpio >/dev/null; then run sudo groupadd --system gpio; fi
        run sudo usermod -aG gpio "$(id -un)"
        if (( kiln_dry_run )); then
            echo '  Write /etc/udev/rules.d/60-kiln-gpio.rules (gpio group access to gpiochip devices)'
        else
            printf '%s\n' 'SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"' \
                | sudo tee /etc/udev/rules.d/60-kiln-gpio.rules >/dev/null
        fi
        run sudo udevadm control --reload-rules
        run sudo udevadm trigger --subsystem-match=gpio
    fi
fi

if [ "$kiln_board" = simulation ]; then
    if [ -x venv/bin/python ]; then
        # Recreating a hardware venv without --system-site-packages would hide
        # its distro GPIO bindings. A preview install must preserve that flag.
        echo '  Reusing the existing Python environment without changing its GPIO access.'
    else
        run python3 -m venv venv
    fi
else
    # Use the distribution's libgpiod bindings, avoiding a second pip gpiod.
    run python3 -m venv --system-site-packages venv
fi
run venv/bin/python -m pip install --upgrade pip
run venv/bin/python -m pip install -r "$kiln_requirements"
run venv/bin/python -m pip check
run venv/bin/python scripts/initialize-settings.py

printf '\n'
printf 'Next: %s\n' "$kiln_next"
printf 'Open %s\n' "$kiln_address"
printf 'Stop the preview with Ctrl+C. Continue with %s before commissioning hardware.\n' "$kiln_guide"
printf '%s\n' \
    'No controller has been started or configured to start on boot.'
if [ "$kiln_board" != simulation ]; then
    echo 'Log out and reconnect before hardware checks to activate GPIO group membership.'
fi
