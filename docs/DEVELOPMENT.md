# Development and board ports

Use a separate checkout for development. Keep the working directory of a live
kiln service for reviewed deployments made while the kiln is idle.

The instructions below target **Linux**, including WSL for a Windows computer.
Python 3.11 is the recorded deployment version. Simulation runs without GPIO,
Blinka or thermocouple packages; it exercises the application and a virtual
kiln, not the wiring or electrical behavior of a real controller.

## Set up a development environment

From the repository directory, with Python and its `venv` support installed:

```bash
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -r requirements-dev.txt
venv/bin/python -m pip check
```

[requirements.txt](../requirements.txt) contains the application dependencies.
[requirements-dev.txt](../requirements-dev.txt) adds the test runner. Hardware
dependencies are separate so that a preview or test run does not install
Raspberry Pi GPIO packages on a computer.

For the installer-assisted route, run `bash setup.sh --board simulation`.
`bash setup.sh --board simulation --dry-run` shows its planned actions first.
See [Getting started](GETTING-STARTED.md) for installation choices.

## Try the interface without hardware

Start a preview from the repository directory:

```bash
bash scripts/run-simulation.sh --port 8082
```

Open <http://localhost:8082/picoreflow/index.html>. Confirm that the dashboard
identifies **simulation**, choose or create a sample program, and start the
virtual firing. Stop the simulated program in the dashboard before pressing
Ctrl+C in the terminal.

The launcher forces simulation and keeps its Settings and recovery files under
`storage/preview/<board>/`, with one directory for each selected profile.
Simulated firing records go to `storage/simulated-firings/`. The launcher does
not start or install a service. Keep the preview on a trusted local network;
the controller API has no login.

To inspect Raspberry Pi's Settings pin choices without Raspberry Pi hardware,
select its profile explicitly:

```bash
KILN_BOARD=raspberry-pi bash scripts/run-simulation.sh --port 8082
```

Use `KILN_BOARD=orange-pi-zero-2w` for the Orange Pi profile. The preview launcher
defaults to Raspberry Pi. When the application is launched directly without a
profile selection, its configuration retains the Orange Pi profile for
compatibility with existing deployments. Changing the profile during simulation
changes the pin choices, not the simulated kiln's physical capabilities.

For a disposable Settings file, supply `KILN_SETTINGS_FILE` as an absolute path:

```bash
kiln_preview_dir="$(mktemp -d)"
KILN_BOARD=raspberry-pi \
KILN_SETTINGS_FILE="$kiln_preview_dir/settings.json" \
bash scripts/run-simulation.sh --port 8082
```

This keeps experimental Settings changes separate from other local settings.
Environment overrides for simulation, port and recovery file take precedence
over saved settings and lock those fields in the interface. Applying settings
from a directly launched process exits it; relaunch the preview if needed.

## Run the tests

Use a fresh Settings path so that local deployment overrides do not change the
defaults expected by the tests:

```bash
kiln_test_dir="$(mktemp -d)"
KILN_SIMULATE=1 \
KILN_SETTINGS_FILE="$kiln_test_dir/settings.json" \
venv/bin/python -m pytest -q Test
```

The test suite must run with application and development dependencies only.
Simulation must not import a GPIO or sensor backend, including through
configuration, Settings or the service's output-off helper. Board-profile
tests check pin serialization and validation without treating mocked GPIO as
hardware evidence.

Run the relevant focused tests while changing behavior, then the full suite
before proposing the change. A passing suite does not validate thermocouple
accuracy, output switching, GPIO timing, power-loss behavior or PID tuning on a
physical kiln. Report those checks separately using the
[build-report template](supported-boards.md#how-a-board-becomes-a-documented-build).

## How hardware selection works

`KILN_BOARD` selects the hardware profile. The provided names are:

| Value | Intended hardware | Physical validation |
| --- | --- | --- |
| `orange-pi-zero-2w` | Orange Pi Zero 2W, with its H616-compatible pin mapping | Existing deployment is documented; changes still require commissioning checks. |
| `raspberry-pi` | The documented Raspberry Pi 3/4 route | Software path provided; Raspberry Pi hardware remains unverified. |

`KILN_SIMULATE=1` selects the virtual kiln independently of that profile. It
must bypass hardware detection and hardware-library imports. Real operation
must verify the selected board before opening GPIO, and must reject a model
that has not been enabled by that profile.

[config.py](../config.py) supplies defaults and loads local Settings.
[The hardware-profile module](../lib/board_profiles.py) defines board
selection and pins. [The Settings store](../lib/settings_store.py) uses the
selected profile to display, validate and serialize pin assignments.
[The oven implementation](../lib/oven.py) chooses the temperature sensor and
controls the heat request. [heater-off.py](../heater-off.py) is the service's
output-off helper; it must not touch GPIO when simulation is selected.

The primary sensor choices are MAX31855 with type K, or MAX31856 with its
supported thermocouple types and MOSI connection. `lib/oven.py` selects software
SPI when clock, MOSI and MISO pins are configured; its hardware-SPI path needs
separate validation if used by a new port. A Blinka board module is only one
piece of this integration.

## Adding a board profile

1. **Identify one exact target.** Record board model/revision, operating-system
   image, architecture, Python and GPIO-library versions. Check that the
   selected Blinka version supports the required GPIO and SPI operations on
   that combination.
2. **Define its pin map once.** Include physical header positions, signal
   names, aliases and default sensor/output pins in the profile. Settings
   choices, validation and serialized values must use the same map. Reject
   duplicate assignments and invalid names. Do not reuse another board's map
   because the connector looks the same.
3. **Detect the hardware before opening it.** Reject unknown or mismatched
   real boards with an actionable error. Scope any Blinka board/chip override
   to that profile. Retain a hardware-free simulation path, even when the
   selected real board is absent.
4. **Handle saved settings deliberately.** Preserve valid existing Orange Pi
   settings and stable serialized pin names. Explain how a user migrates when
   moving settings between boards; never silently reinterpret a pin belonging
   to one board as a different board's output.
5. **Extend installation and service configuration.** Specify the OS packages,
   Python hardware dependencies, GPIO permissions and device requirements.
   Make account/path/profile selection explicit. Confirm that the service's
   start/stop hooks honor simulation and the selected output-off level.
6. **Add meaningful software checks.** Test selection and rejection, Settings
   round trips, invalid and duplicate pins, existing-setting compatibility,
   and startup in simulation with hardware imports unavailable. Test actual
   failure behavior rather than repeating the contents of the pin table.
7. **Write the matching build guide.** Include a board-specific pin diagram,
   exact sensor and driver interfaces, OS preparation, install commands,
   expected results and troubleshooting. Identify untested steps honestly.
8. **Complete physical validation before claiming a tested build.** With kiln
   mains isolated, verify sensing, fault response and the output's off state
   through idle, boot, shutdown and controller power loss while the driver
   supply remains powered. Follow the hardware guide for the independent
   cutoff and mains work, then document supervised commissioning.

Put the evidence, limitations, date and revision in a build report before
changing the [compatibility status](supported-boards.md). Simulation and a
successful install are useful milestones; neither establishes the behavior of
the electrical installation.

## Other useful references

- [Raspberry Pi MOSFET interface and build](builds/raspberry-pi.md)
- [Orange Pi relay interface and kiln power](HARDWARE.md)
- [Board alternatives and historical inventory](supported-boards.md)
- [HTTP and WebSocket API](api.md)
- [PID tuning](pid_tuning.md)
- [Automatic ramp correction](automatic-ramp-control.md)
- [Orange Pi installation and maintenance](INSTALL.md)
