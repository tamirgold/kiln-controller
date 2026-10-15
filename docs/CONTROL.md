# Control and power-loss recovery

This guide explains how a firing progresses and how the controller responds to
temperature changes and interruptions. For ordinary use, start with the
[user guide](USER-GUIDE.md). Change controller values through
[Settings](SETTINGS.md) after completing the matching [build guide](GETTING-STARTED.md).

## Temperature sensing and protection

The controller supports MAX31855 with type K, or MAX31856 with B/E/J/K/N/R/S/T
thermocouples. It uses median sampling, requires fresh valid readings before
heating, and supports over-temperature and sensor-fault shutdown. Keep fault
overrides disabled for normal operation. MAX31856's configurable 50 Hz filter
does not apply to MAX31855.

Match the converter, probe and wiring to the [hardware guide](HARDWARE.md).
MAX31855 requires an ungrounded, electrically insulated probe. Sensor ratings,
calibration and electrical isolation still need to be checked on the real build.

The controller has one heat request. It does not independently control three
temperature zones. Software protection cannot disconnect a failed-closed SSR;
the kiln needs an independent temperature limiter and a suitable hardwired
shutdown circuit.

## PID, ramps and holds

PID adjusts heater duty to approach and maintain the target temperature. Inside
its control window it regulates duty, with automatic integral windup protection
outside that window. A **ramp** changes target temperature over time; a **hold**
keeps the target steady.

Optional catch-up pauses schedule progress on a heating ramp when the kiln is
too cold, on a cooling ramp when it is too hot, and during a hold when
temperature is outside the allowed window on either side. A ramp advances
when temperature is already ahead of its target; PID still controls heater
output. This is why elapsed firing time and scheduled program time can differ.

Warm-start seek can skip initial schedule points when starting with a warm kiln.
Low-temperature throttling limits requested power outside the PID window when
the target is below its configured threshold.

### Catch-up tolerance and the PID window

**Catch-up temperature tolerance** can be set independently of the **PID control
window**. Zero uses the PID window for both, preserving the earlier behavior.
Set a positive catch-up tolerance when tuning so that widening the PID window
does not also loosen temperature waits during ramps or holds.

Tune gains for the kiln and its relay period. Shortening a mechanical relay's
cycle is not a substitute for tuning. The [recorded ramp-tuning example from
5 October 2026](ramp-tuning-20261005.md) and its
[high-temperature follow-up](high-temperature-smoothing-20261005.md) describe
one installation. The latter covers gentler gains and retaining a recent
integral bias across a brief, healthy recovery to reduce cycling and restart
dips. These examples are not universal PID settings.

### Automatically correct ramp speed

Automatic ramp correction compares a multi-minute temperature trend with the
active segment once a minute and applies bounded heater-power corrections.
The **Ramp tracking** panel shows the requested and measured rates, applied
adjustment and any limiting condition.

The correction preserves temperature waits, holds, relay timing and the original
planned graph. Read [automatic ramp control](automatic-ramp-control.md) for
measurement timing, limits and diagnostics. Historical heating-capacity
measurements are a separate feature: they guide program editing without
retuning PID gains or rewriting schedules.

## Power-loss recovery

Automatic recovery restores saved program progress after an eligible
interruption. It requires all of the following:

- A recent valid **RUNNING** recovery record.
- Matching simulation/real mode and temperature units.
- A valid schedule and saved program progress.
- A ready sensor with fresh readings.
- Synchronized Chrony time when that check is configured.

Outage time does not advance the program or accrue energy. An eligible recovery
continues the same firing history record. Paused, stopped, completed, expired,
corrupt and mismatched records do not automatically resume.

Enable recovery only when you intend automatic resumption, using the maximum
delay and clock settings appropriate to the installation. See the
[installation guide](INSTALL.md) for commissioning and clock checks.

### Stop, pause and restart are different actions

| Action | Effect |
| --- | --- |
| **Stop firing** | Switches the heat request off and cancels automatic recovery of that firing |
| API **pause** | Maintains temperature and can continue heating; it is not a dashboard button |
| API **resume** | Continues a paused firing; see the [API guide](api.md) |
| Restart or stop the service during a firing | Preserves recovery progress and may allow recovery; it is not equivalent to Stop firing |
| Close or disconnect the browser | Leaves the controller operating |

The service and controller attempt to switch the heat request off on exit.
An uncaught controller-thread fault also stops output. These actions cannot
prove that mains power is absent or substitute for electrical isolation.
Verify output-off behavior at boot, shutdown and controller power loss with
kiln mains isolated, including when a separate driver supply remains powered.

## Simulation

Simulation provides an adjustable thermal model and speed multiplier for
exploring the interface and schedules without hardware heating. Follow the
[getting-started guide](GETTING-STARTED.md) for a preview with its own state file
and port, and verify that the dashboard identifies simulation before starting
a program.

Simulated records and statistics are kept separately from real firings.
Simulation is not evidence of real sensor calibration, wiring behavior,
heating capacity or suitable PID gains.

## Advanced tools

- [Manual PID tuning](pid_tuning.md) and [PID autotuning](ziegler_tuning.md).
- [API and PID diagnostics](api.md).
- [OS-based scheduling with at](schedule.md).
- [Optional Slack watcher](watcher.md).

These are separate tools, not dashboard features. Review their scripts and
dated examples before use. Sensor/output tests and autotuning can access real
hardware; the output-toggle script is not a routine check on a powered kiln.
