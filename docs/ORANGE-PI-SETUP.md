# Orange Pi Zero 2W kiln controller

> Historical deployment record from September 2026. Deployment-specific settings,
> firing history, and verification screenshots remain local and are not included
> in this repository. The tracked source defaults use `gpio_heat_invert=False`
> and a two-second control cycle; the documented deployment uses active-low
> output and a 30-second cycle through local settings overrides. These notes
> describe past deployments, not the current source defaults.

Web interface: http://192.168.68.54:8081
Hostname: http://orangepizero2w.local:8081 (where local name resolution works)
SSH: `ssh orangepi@192.168.68.54`
Installation: `/home/orangepi/kiln-controller`
Service: `kiln-controller.service`

Configured for a MAX31855, Celsius, and automatic recovery within 15 minutes.
The controller uses real GPIO and sensor input, not simulated temperatures.

## MAX31855 wiring

These are **physical pin numbers on the Orange Pi Zero 2W's 40-pin header**.
Connect with the board powered off. Use 3.3 V logic and power.

| MAX31855 module | Physical pin | Orange Pi signal |
| --- | --- | --- |
| VCC / compatible VIN input | 1 | 3.3 V |
| GND | 6 | Ground |
| DO / SO | 21 | PH8, GPIO 232 |
| CLK / SCK | 23 | PH6, GPIO 230 |
| CS | 24 | PH5, GPIO 229 |

Leave physical pin 19 (MOSI) unconnected; MAX31855 is read-only.
Connect the thermocouple leads to the module's + and - terminals. The common
MAX31855K requires a K-type thermocouple. Check the board labels: an output
labelled 3Vo on an Adafruit breakout is not its VIN input.

## SSR control wiring

| Connection | Physical pin | Signal |
| --- | --- | --- |
| Relay module IN1 | 37 | PI16, GPIO 272; LOW = heat request, HIGH = off |
| SSR driver's logic ground | 39 | Ground |

Use a driver that accepts 3.3 V logic and supplies the SSR's required input
voltage/current. The exact SSR model/input rating is still needed to specify
its power and driver-side connections. Do not assume the GPIO can directly
supply an SSR just because its label says 3-32 V DC.

For the active-low relay module installed on 24 September, use a 10 kohm
pull-up between pin 37 and 3.3 V (pin 17); remove any previous pull-down. This biases the heating request off
while the 3.3 V rail is powered; it does not guarantee OFF if that rail loses
power while the driver remains powered. Verify the actual behavior during
boot, shutdown, and controller power loss with kiln mains isolated. Use a suitable
independent over-temperature cutoff for the kiln; software cannot interrupt
a failed-closed SSR.

The pin mapping is verified against the manufacturer's manual and this board's
`gpio readall` output. Reference:
http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_Zero_2W

## Startup and recovery

The systemd service starts automatically at boot and restarts after a process
failure. The output is driven to its configured inactive level before startup and after
the process exits (HIGH with the current active-low relay module).

During a firing, progress is saved every control cycle (nominally 2 seconds)
to `/home/orangepi/kiln-controller/state.json`. Writes use a temporary file,
fsync, and atomic replacement to avoid truncated progress after a power cut.
The saved state includes the program data, elapsed program time, temperature
units, and cost.

Automatic recovery requires all of the following:
- The saved program was RUNNING and the state is no older than 15 minutes.
- The saved state is valid and belongs to real operation in Celsius.
- Chrony has synchronized the board's clock, so the outage age is reliable.
- The thermocouple has enough valid, recent readings.

Recovery continues at the saved program position; outage time is not added to
the program. The kiln can then wait to catch up to its target temperature.
Stop cancels automatic recovery. Paused, completed, corrupt, expired, or
simulation states do not automatically start heating.

## Original installation status (historical)

At installation the sensor test reported `thermocouple not connected`.
The real service remains IDLE with heat off and shows a warning in the web UI.
Connect the MAX31855 and thermocouple, then verify a plausible room-temperature
reading and a response when the probe is warmed before attempting a firing.

SSR input specifications and live heater operation have not been verified.
PID gains are converted starting values, not tuned for this kiln. The software
emergency limit is 1240 C (equivalent to upstream's 2264 F); lower it if your
kiln or load requires a lower maximum. The configured heater power is 11 kW and the electricity tariff is
ILS 0.645/kWh, displayed with the shekel symbol. Existing accumulated cost
was not recalculated; the previously identified cost-calculation bugs
still require correction before the displayed totals can be trusted.
All five bundled sample profiles were converted from Fahrenheit to Celsius.

## Maintenance

```sh
sudo systemctl status kiln-controller
sudo systemctl restart kiln-controller
journalctl -u kiln-controller -n 50 --no-pager
curl http://127.0.0.1:8081/api/health
```

Configuration: `/home/orangepi/kiln-controller/config.py`
Profiles: `/home/orangepi/kiln-controller/storage/profiles/`
Installed package versions: `/home/orangepi/kiln-controller/requirements-installed.txt`

To run the independent sensor test, stop the service first so that two
processes do not claim the same GPIO lines:

```sh
sudo systemctl stop kiln-controller
cd /home/orangepi/kiln-controller
timeout 10 venv/bin/python -u test-thermocouple.py
sudo systemctl start kiln-controller
```

## Changes and validation

Upstream commit: `a2b3071e4e55f47c20326563200da0b49d3c5bb8`.
Local adaptations include the verified H616-compatible GPIO mapping for this
H618 board, systemd startup, Celsius profiles/settings, atomic recovery state,
a fresh-sensor heating guard, a visible sensor warning, and output cleanup.
Avoid overwriting these local changes with an upstream checkout.

- 25 automated tests passed on the Orange Pi, including recovery eligibility,
  corrupt state, failed atomic replacement, Stop, and missing/stale sensor guards.
- A separate simulated service was killed abruptly with SIGKILL and recovered
  the same program at its saved 120-second position in Celsius.
- The simulation stayed idle for expired/corrupt states and after Stop/restart.
- The real service stayed idle with heat off throughout recovery tests.
- The web interface and health endpoint responded over the LAN.
- A real reboot changed boot ID from d852f31e-9970-42e2-b573-d40179e8f335
  to 53e690c4-63f6-4d78-9bdd-c8f959b45df0. The enabled service started
  automatically with no process restarts; pin 37 read LOW.
- Chrony synchronized successfully after reboot (Leap status: Normal).
- Physical sensor wiring, temperature accuracy, and SSR switching require
  verification after the hardware is connected. No real firing was started.

## Settings applied on 2026-09-23

- kw_elements = 11.0
- kwh_rate = 0.645
- currency_type = "₪"
- throttle_percent = 100

The optional 20% warmup restriction is removed. Full demand now permits
100% output; PID modulation near the target and the temperature/sensor
protections remain active.

The user authorized a service restart during firing. The controller
automatically resumed test-fast at saved runtime 3824.01 seconds, and
verification showed RUNNING at 3826.04 seconds with a valid sensor, the
new tariff/currency, and PID output 1.0. The log confirmed heat_on=2.00
and heat_off=0.00 for a full-power cycle. No program was started over.


Current relay wiring and verified settings: see RELAY-MODULE-CHANGE.md.
The relay control cycle is now 30 seconds; status updates remain every two seconds.
