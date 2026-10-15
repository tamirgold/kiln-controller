#!/usr/bin/env bash
# A hardware-free preview with a separate recovery record.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
kiln_preview_port=${KILN_PORT:-8081}
while (($#)); do
    case "$1" in
        --port)
            if (($# < 2)); then echo '--port needs a value.' >&2; exit 2; fi
            kiln_preview_port=$2; shift 2 ;;
        -h|--help)
            echo 'Usage: bash scripts/run-simulation.sh [--port 8081]'
            echo 'Runs the simulator only; does not import GPIO or use the normal recovery file.'
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done
if [[ ! "$kiln_preview_port" =~ ^[0-9]{1,5}$ ]] || ((10#$kiln_preview_port < 1 || 10#$kiln_preview_port > 65535)); then
    echo 'Choose a port from 1 to 65535.' >&2; exit 2
fi
if [ ! -x venv/bin/python ]; then
    echo 'Install first: bash setup.sh --board simulation' >&2; exit 1
fi
export KILN_SIMULATE=1
export KILN_BOARD=${KILN_BOARD:-raspberry-pi}
case "$KILN_BOARD" in
    raspberry-pi|orange-pi-zero-2w) ;;
    *) echo 'KILN_BOARD must be raspberry-pi or orange-pi-zero-2w.' >&2; exit 2 ;;
esac
kiln_preview_directory="$PWD/storage/preview/$KILN_BOARD"
mkdir -p "$kiln_preview_directory"
export KILN_PORT=$kiln_preview_port
export KILN_SETTINGS_FILE=${KILN_SETTINGS_FILE:-$kiln_preview_directory/settings.json}
export KILN_STATE_FILE="$kiln_preview_directory/state.json"
echo "Simulation: http://localhost:$KILN_PORT/picoreflow/index.html (Ctrl+C to stop)"
exec venv/bin/python kiln-controller.py
