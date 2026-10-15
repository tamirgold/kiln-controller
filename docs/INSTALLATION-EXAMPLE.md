# Recorded Orange Pi installation

This page preserves the example configuration and screenshots previously
included in the README. The values below were checked against the running
Orange Pi Zero 2W installation on **4 October 2026**. They are a dated record,
not a statement of today's live settings or recommended defaults for other
kilns.

For a new installation, choose the matching route in the
[getting-started guide](GETTING-STARTED.md). The [Raspberry Pi build](builds/raspberry-pi.md)
uses an active-high MOSFET interface; the [Orange Pi software](INSTALL.md) and
[hardware](HARDWARE.md) guides retain the relay arrangement recorded here.
Inspect the current source and applied Settings instead of using this snapshot
as a commissioning configuration.

## Source defaults and installation values recorded on 4 October 2026

`config.py` supplied source defaults; local `settings.json` overrides selected
values on the installation. Both columns below describe the record made on
4 October, even if source defaults or live settings have changed since then.

| Setting | Source default recorded then | Installation recorded then |
| --- | --- | --- |
| Operating mode | Real hardware | Real hardware |
| Installed heating power | 11 kW | 8 kW |
| Tariff and currency | ₪0.645/kWh | ₪0.645/kWh |
| Temperature units | Celsius | Celsius |
| Converter / thermocouple | MAX31855 / K | MAX31855 / K |
| Control cycle | 2 seconds | 30 seconds |
| Output polarity (`gpio_heat_invert`) | `false`: active high | `true`: active low |
| Automatic recovery window | 15 minutes | 25 minutes |
| Over-temperature limit | 1240°C | 1240°C |

The photographed 8 kW kiln's estimated cost for one hour of heater on-time was
₪5.16 at ₪0.645/kWh. The software uses installed power for energy estimates;
this figure is not a measurement of actual mains power.

The documented mechanical relay used an active-low input and a 30-second
control cycle. Its contacts switched a regulated 5 V supply into the DC-input
SSR rather than switching kiln mains. The external pull-up biased the request
off only while its 3.3 V supply existed. Verify your exact module and its
behavior through boot, shutdown and controller power loss.

## Images and dated notes

The October 4 dashboard, program editor and history screenshots are retained
in the [user guide](USER-GUIDE.md). The settings screenshots are retained in
the [settings guide](SETTINGS.md). Readings change during a firing and images
do not prove a different board or configuration works.

- [Relay module change record](RELAY-MODULE-CHANGE.md): the earlier module and
  its specific wiring/pull-up arrangement.
- [Ramp-tuning record, 5 October 2026](ramp-tuning-20261005.md): catch-up and
  tuning observations from this installation.
- [High-temperature follow-up, 5 October 2026](high-temperature-smoothing-20261005.md):
  gentler gains and recovery behavior from the same installation.
- [Historical Orange Pi setup](ORANGE-PI-SETUP.md) and
  [historical UI notes](UI-UPDATE.md): earlier deployment details.

Use the current build guide for your board for instructions. Retain
these records as context for changes, not as settings to copy wholesale.
