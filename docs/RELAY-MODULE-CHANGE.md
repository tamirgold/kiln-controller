# Relay module installed — 24 September 2026

> Historical deployment record from September 2026. Deployment-specific settings,
> firing history, and verification screenshots remain local and are not included
> in this repository. The tracked source defaults use `gpio_heat_invert=False`
> and a two-second control cycle; the documented deployment uses active-low
> output and a 30-second cycle through local settings overrides. These notes
> describe past deployments, not the current source defaults.

Applied on the Orange Pi after the user confirmed mains isolation and that
IN1-to-GND turns relay 1 on and releasing IN1 turns it off.

- Physical pin 37 / PI16 remains the control output.
- gpio_heat_invert = True: LOW turns relay 1 on; HIGH turns it off.
- sensor_time_wait = 30 seconds, to reduce mechanical relay cycling.
- The watcher publishes live status every two seconds independently of the
  relay cycle, preserving dashboard freshness and ten-second history sampling.
- Temperature sampling/averaging follows the 30-second control cycle. Allow
  about 30 seconds for a complete sensor sample set after startup.

The former firing was stopped and its final record retained. Automatic
recovery of that stopped firing was cancelled. After restart, the controller
was IDLE, physical pin 37 was OUTPUT HIGH, and heat demand was zero. The service
remains enabled at boot. Live websocket frames arrived about 2.00 seconds apart.
Mock GPIO tests verified startup OFF, ON and return to OFF for both polarities.

The thermocouple had reported approximately 0 C during wiring. After restart,
it reported approximately 133 C. Verify that this matches the actual kiln before
reconnecting mains. No new firing or software relay-ON test was initiated.

Wiring (physical Orange Pi header pins):
- Pin 1 -> MAX31855 VCC; pin 17 (3.3 V) -> relay module VCC.
- Pin 2 (5 V) -> JD-VCC; remove the JD-VCC/VCC jumper.
- Pin 39 -> module GND; pin 37 -> IN1.
- 10 kohm pull-up from IN1 to 3.3 V for active-low boot behavior; remove any
  previous pull-down. The pull-up installation has not been remotely verified.
- 5 V -> K1 COM; K1 NO -> SSR input +; ground -> SSR input -.
- Leave K1 NC unused. Relay contacts switch the SSR DC input, not kiln mains.

Other draft settings were preserved: 5.5 kW, 150 C throttle threshold, 50 Hz
filter flag, and 25-minute recovery. Those remain pending. The old five-second
cycle in that draft was replaced by the applied 30-second relay cycle.

Backup: /home/orangepi/kiln-backups/relay-20260924T081623Z
Active configuration: /home/orangepi/kiln-controller/settings.json
Pending configuration: /home/orangepi/kiln-controller/settings.pending.json
