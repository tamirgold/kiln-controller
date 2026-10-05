# Ramp tracking on the Orange Pi kiln — 5 October 2026

The warm firing starting at 736.5°C requested 61.7647°C/hour toward 950°C.
Over the last hour before tuning, measured temperature rose only 34.26°C/hour.
The last 126 logged control cycles contained 64 fully-on cycles, 61 fully-off
cycles and one partial-power cycle. The derivative term reached 92.59 percentage
points, while the integral contribution was only 2.59 near the end of the sample.
The temperature troughs repeatedly exceeded the 2.7778°C catch-up tolerance,
discarding program time and reducing the average ramp speed.

This was a control issue. The chart correctly retained elapsed time and the
original planned ramp. Historical readings and their time origin were preserved.

The installed settings were changed as follows:

| Parameter | Before | After |
|---|---:|---:|
| Kp | 18 | 8 |
| Inverse Ki | 44.4444444444 | 44.4444444444 |
| Kd | 397.5029623847 | 100 |
| PID control window | 2.7777777778°C | 10°C |
| Catch-up tolerance | Follow PID window | Explicit 2.7777777778°C |
| Relay period | 30 seconds | 30 seconds |
| Samples per period | 10 | 10 |

The wider PID window permits proportional control and integral accumulation
through the recorded temperature ripple. Lower P and D gains reduce repeated
full-power/off reversals. Independent catch-up tolerance keeps all existing
heating, cooling and hold waits at their previous temperature threshold. Sensor
fault shutdown, overtemperature protection and the original program are unchanged.

Five response models fitted to recent readings, using actual 30-second on/off
pulses, strict catch-up tolerance and added measurement disturbance, predicted
60.9–62.2°C/hour after settling with these settings. They reproduced about
33.5–36.9°C/hour with the previous settings. The models predicted approximately
five to six minutes of initial catch-up with a zero integral and a 7°C deficit.
These estimates cover the observed 736–855°C region, not a full-range kiln
calibration; measurements after deployment are needed to judge the result.

Deployment at 13:09 UTC stopped the controller, saved its fresh state, changed
only the reviewed source/settings, and resumed the same firing from exactly
41172.030491 program seconds. No warm seek or program-time jump was performed.
Original firing identity, elapsed origin, history, energy and cost were checked.
The preceding delay remains visible; restoring the ramp slope cannot erase it.

Validation before deployment: 165 Linux tests passed, including independent
catch-up thresholds, legacy settings migration, holds, recovery, sensor shutdown,
and deployment rollback after injected file-write failures. A Node check exercised
the actual settings unit-conversion function for Celsius/Fahrenheit and zero
fallback. Deployment verified active settings and source hashes after recovery.

## Measured response after deployment

Twenty minutes of read-only observation followed the restart. In the final
ten-minute window, the measured linear temperature trend was **61.10°C/hour**
against the requested **61.76°C/hour**. All 21 represented control cycles used
partial power. Temperature scatter around its linear trend fell from about
3.08°C standard deviation before tuning to 1.33°C. The average target deficit
was 0.74°C; individual samples ranged from 3.75°C above to 3.93°C below target.

Catch-up remained enabled and occupied about 10% of this window, down from
43% before tuning. Program progress across control-cycle timestamps was about
90% of wall time: 55.54°C/hour of target advancement, with two paused intervals
out of twenty. Aligning the temperature fit to completed cycles gives 51.7°C/hour
instead of 61.1°C/hour, showing sensitivity to the last pulse and rebound. The
temperature slope alone therefore does not establish exact ramp matching or an
exact finish time. The remaining occasional waits and all prior delay are still
visible. The new response is substantially closer to the requested ramp; it is
not a guarantee of exact tracking throughout the remaining temperature range.

The running settings page and original warm-start graph were checked after
deployment: the 736.5°C start, 9h29m offset, original planned endpoint, and history
were retained. No browser errors or browser control writes occurred.
