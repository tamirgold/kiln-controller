# Install on an Orange Pi Zero 2W

This guide installs this repository on an Orange Pi Zero 2W running Debian 12
(Bookworm), with Python 3.11 and the distro's GPIO bindings. Other Debian or
Ubuntu images need compatible GPIO devices and should be checked before use.
The current configuration uses the H618 board's H616-compatible pin mapping;
it is not a generic Raspberry Pi installation.

Commands below run on the Orange Pi as `orangepi`. The service expects the
repository at `/home/orangepi/kiln-controller`. If you use another account or
directory, adjust the service before installing it.

Keep kiln mains isolated while configuring wiring and output polarity. The
tracked defaults select real hardware, an active-high output, and a two-second
control cycle. Incorrect polarity can request heat even while the controller
says it is idle. Use an independent over-temperature cutoff and suitable mains
protection; software cannot disconnect a failed-closed SSR.

## 1. Install operating-system dependencies

```bash
sudo apt update
sudo apt install git ca-certificates build-essential python3-dev python3-venv \
  python3-libgpiod gpiod libgpiod-dev chrony avahi-daemon curl
sudo systemctl enable --now chrony avahi-daemon

getent group gpio >/dev/null || sudo groupadd --system gpio
sudo usermod -aG gpio orangepi
printf '%s\n' 'SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"' \
  | sudo tee /etc/udev/rules.d/60-kiln-gpio.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=gpio
```

Log out and reconnect so the new group membership takes effect. Then check:

```bash
id
ls -l /dev/gpiochip*
gpiodetect
chronyc tracking
```

Your account must belong to `gpio`, and the GPIO devices must allow that group
to read and write. Blinka selects the main GPIO chip using
`/sys/class/gpio/gpiochip0/label`; an image that does not expose this interface
needs investigation before proceeding.

Chrony supplies the clock-synchronization check used by automatic recovery.
Avahi advertises the board's hostname on the local network. If `.local` names
do not resolve on your client, use the board's IP address instead.

## 2. Clone your repository

The repository is private. With an SSH key already authorized for your GitHub
account:

```bash
cd /home/orangepi
git clone git@github.com:tamirgold/kiln-controller.git
cd kiln-controller
```

Alternatively, clone `https://github.com/tamirgold/kiln-controller.git` using an
authenticated Git credential helper. GitHub account passwords do not work for
Git operations over HTTPS; do not put a token in the clone URL.

In a fresh clone, `config.py`, `requirements.txt`, and `kiln-controller.py` are
directly inside `kiln-controller/`.

## 3. Create the Python environment

Use system site packages so the virtual environment can import the distro's
`python3-libgpiod`. Exclude `RPi.GPIO`, which is for Raspberry Pi hardware.

```bash
python3 -m venv --system-site-packages venv
venv/bin/python -m pip install --upgrade pip
kiln_requirements="$(mktemp)"
sed '/^[[:space:]]*RPi\.GPIO[[:space:]]*$/d' requirements.txt > "$kiln_requirements"
venv/bin/python -m pip install -r "$kiln_requirements" \
  'Adafruit-Blinka==9.2.0' pytest
rm "$kiln_requirements"
venv/bin/python -m pip check
```

Blinka 9.2.0 is a recorded working version for this installation, not a complete
dependency lock. It supports both libgpiod 1.x and 2.x Python APIs. Debian 12
provides the 1.x bindings; newer distributions may provide 2.x and different
GPIO command-line syntax. Prefer the distro bindings instead of installing a
second pip `gpiod` package that masks them.

Verify imports and the selected pins:

```bash
venv/bin/python - <<'PY'
import config
import gpiod
from importlib.metadata import version

print("Blinka:", version("Adafruit-Blinka"))
print("gpiod module:", gpiod.__file__)
print("gpiod API:", "2.x" if hasattr(gpiod, "LineSettings") else "1.x")
for name in ("spi_sclk", "spi_miso", "spi_cs", "spi_mosi", "gpio_heat"):
    print(name, getattr(config, name).id)
PY
```

The GPIO offsets should be 230, 232, 229, 231, and 272, respectively; the chip
number can depend on the kernel. This check imports the configuration without
starting a kiln or requesting heater output. Imports still open GPIO chip
devices, including in simulation, so the current simulator requires this
compatible Linux environment.

## 4. Preview the interface in simulation

Start a preview directly from the shell with a separate recovery file and port:

```bash
mkdir -p storage/preview
KILN_SIMULATE=1 \
KILN_STATE_FILE="$PWD/storage/preview/state.json" \
KILN_PORT=8082 \
venv/bin/python kiln-controller.py
```

Open `http://orangepizero2w.local:8082/picoreflow/index.html`, substituting the
board's hostname or IP address when necessary. Confirm that the interface
identifies simulation before starting a sample program. Stop the simulated
program, then press Ctrl+C in the terminal when finished.

Simulated firing records go to `storage/simulated-firings/`. The separate
preview state file avoids overwriting the normal recovery record. The three
environment overrides also lock their corresponding Settings fields; use the
installed service for permanent configuration changes.

The service's startup and shutdown hooks access the heater GPIO even when
simulation is selected. Review polarity before installing the service.

## 5. Set local hardware configuration

Read [config.py](../config.py) and match every setting to your installation.
The [Settings page](../public/settings.html) manages validated overrides in
`settings.json`; saved edits remain separate in `settings.pending.json` until
applied. Both files are intentionally excluded from Git.

For a **new installation with the documented active-low relay wiring only**,
create `settings.json` with this initial content. **Do not overwrite an
existing settings file.** Use a different polarity or cycle if your driver
requires it.

```json
{
  "version": 1,
  "values": {
    "simulate": true,
    "gpio_heat_invert": true,
    "sensor_time_wait": 30,
    "automatic_restarts": false
  }
}
```

This partial file merges with the source defaults. It starts in simulation,
uses HIGH for off and LOW for a heat request, and keeps automatic recovery
disabled during commissioning. It does not reproduce every setting on the
photographed controller.

Review these defaults before real operation:

| Setting | Tracked default | What to verify |
| --- | --- | --- |
| Sensor | MAX31855, type K | Converter, thermocouple type, wiring, and calibration |
| Temperature units | Celsius | Programs, limits, and displayed readings |
| Heating power | 11 kW | Actual installed element power for energy and cost estimates |
| Electricity tariff | ₪0.645/kWh | Your tariff and currency |
| Emergency limit | 1240°C | A limit within the kiln, load, and sensor ratings |
| PID gains | Celsius starting values | Tune for your kiln; defaults are not commissioning results |
| Recovery | Enabled, 15-minute window | Disabled by the example above until explicitly enabled |

The standard MAX31855 connections use **physical pins** on the 40-pin header:

| Connection | Physical pin | Signal |
| --- | ---: | --- |
| MAX31855 power | 1 | 3.3 V |
| MAX31855 ground | 6 | Ground |
| DO / MISO | 21 | PH8, GPIO offset 232 |
| CLK | 23 | PH6, GPIO offset 230 |
| CS | 24 | PH5, GPIO offset 229 |
| Relay heat request | 37 | PI16, GPIO offset 272 |
| Relay logic ground | 39 | Ground |

Leave MOSI, physical pin 19, disconnected for MAX31855. MAX31856 requires MOSI
and the corresponding sensor selection. Its 50 Hz filter setting does not
apply to MAX31855.

The documented active-low relay uses an external 10 kΩ pull-up from IN1/pin 37
to 3.3 V, so the heat request is off when GPIO is released. Its relay contacts
switch the SSR's DC control input, not kiln mains. See the dated
[relay wiring record](RELAY-MODULE-CHANGE.md) for that specific module; verify
your own module's input and power requirements.

With mains still isolated, verify a plausible physical sensor reading and its
response to warming the probe. Stop any controller process first; on an
existing service installation, use `sudo systemctl stop kiln-controller` only
after the kiln is idle. Then run:

```bash
timeout 15 venv/bin/python -u test-thermocouple.py
```

This reads the physical sensor even if simulation is enabled. Do not run
multiple processes that claim the same GPIO lines. `test-output.py` deliberately
toggles the heater request and is not a routine installation check.

## 6. Install the service and commission real operation

After verifying wiring, polarity, and the configured off level, inspect
[kiln-controller.service](../lib/init/kiln-controller.service). Adjust its
account and paths if they differ from this guide, then install it:

```bash
sudo install -m 0644 lib/init/kiln-controller.service \
  /etc/systemd/system/kiln-controller.service
sudo systemctl daemon-reload
sudo systemctl enable --now kiln-controller
sudo systemctl status kiln-controller --no-pager
curl http://127.0.0.1:8081/api/health
```

The service uses group `gpio`, attempts to set the configured off level before
startup and after exit, and restarts failures after five seconds. With the
example local settings above, it initially runs in simulation.

Open `http://orangepizero2w.local:8081/picoreflow/settings.html`. Review Sensor &
wiring, Firing behavior, PID control, Protection overrides, and Electricity &
display. Leave protection overrides disabled. When commissioning is ready and
the kiln is idle, switch Simulation off, save, review, and apply the change.
Confirm a fresh, plausible sensor reading and zero heat demand before a firing.
With a 30-second control cycle, allow about 30 seconds for the initial complete
sensor sample window.

Save creates a pending draft; it does not affect a running firing. Apply
requires an idle kiln with no eligible recovery waiting to resume. It activates
the settings and exits the process with status 75 so systemd can restart it.
When launched directly in a terminal, you must relaunch after applying.
Active settings override `config.py`; environment variables override and lock
simulation mode, port, and recovery path when supplied.

Keep the controller on a trusted local network. Its HTTP control API has no
user login; do not expose port 8081 directly to the Internet.

## 7. Recovery, tests, and routine checks

Enable automatic recovery in Settings only when you want it. Recovery requires
a valid recent RUNNING record, matching units and simulation mode, valid program
progress, and fresh sensor readings. Real operation also requires a synchronized
Chrony clock when that check is enabled. It resumes saved program progress;
outage time is not added to the program.

Paused, stopped, completed, expired, corrupt, or mismatched-mode records do not
automatically resume. Stop in the dashboard cancels recovery. Stopping or
restarting the service during a firing preserves its recovery record and may
allow that firing to resume.

```bash
chronyc tracking
journalctl -u kiln-controller -n 100 --no-pager
curl http://127.0.0.1:8081/api/health
```

Run the test suite on the configured Linux environment, using a fresh settings
path so deployment overrides do not change the defaults expected by the tests:

```bash
kiln_test_dir="$(mktemp -d)"
KILN_SIMULATE=1 KILN_SETTINGS_FILE="$kiln_test_dir/settings.json" \
  venv/bin/python -m pytest -q Test
```

The suite uses simulated or mocked heater paths, but imports still need the
board's Python/GPIO environment. Passing tests does not verify physical wiring,
temperature calibration, relay behavior, or PID tuning.

## 8. Back up and update

Update only while the kiln is idle. Preserve `settings.json`,
`settings.pending.json`, `state.json`, and all of `storage/`, including programs,
firing records, and settings backups. They are not all stored in Git.

From `/home/orangepi/kiln-controller`:

```bash
sudo systemctl stop kiln-controller
kiln_backup="$HOME/kiln-controller-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
tar --exclude='./venv' --exclude='./.git' -czf "$kiln_backup" .
git status --short
git pull --ff-only
```

Resolve any local source changes deliberately if Git cannot fast-forward.
Repeat the filtered dependency installation from step 3 if requirements have
changed, then run the tests from step 7. If the service file changed, review and
reinstall it using step 6. Finally:

```bash
sudo systemctl start kiln-controller
sudo systemctl status kiln-controller --no-pager
journalctl -u kiln-controller -n 50 --no-pager
curl http://127.0.0.1:8081/api/health
```

Confirm the expected mode, settings, and idle state in the dashboard before
using the kiln again.
