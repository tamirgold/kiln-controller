# Smoother control near 1,000°C

The firing on 5 October 2026 tracked about 59.63°C/hour between 900°C and 950°C,
then slowed to 51.97°C/hour over the last 30 minutes near 1,000°C against a
60°C/hour segment. Its average heater duty was 69.7%, so continuous full-power
saturation did not explain this loss. The last 20 logged control cycles ranged
from 23.6% to 100% power. One low-power command left the heater off for 22.91
seconds; subsequent cycles returned to full power. The thermocouple reported
drops up to 3.97°C over roughly ten seconds. These are sensor measurements,
not evidence that the entire load cools at that instantaneous rate.

Large proportional and derivative responses amplified the cycling. Troughs
repeatedly crossed the 2.7778°C catch-up threshold and paused the program.
The automatic ramp observer's uncertainty band widened with the oscillation,
so modest sustained rate deficits did not trigger additional trim. The fix
reduces the inner controller's oscillation while retaining the observer's
noise protection and the temperature waits.

## Installed tuning

| Setting | Before | First adjustment | Final adjustment |
| --- | ---: | ---: | ---: |
| Kp | 8 | 6 | 4 |
| Inverse Ki | 44.4444444444 | 60 | 90 |
| Kd | 100 | 30 | 30 |
| PID window | 10°C | 10°C | 10°C |
| Catch-up tolerance | 2.7778°C | 2.7778°C | 2.7778°C |
| Relay cycle | 30 seconds | 30 seconds | 30 seconds |
| Sensor samples per cycle | 10 | 10 | 10 |

These gains are installation settings, not new generic defaults. The integral
time scale is nearly preserved (Kp × inverse Ki: 355.6 → 360 seconds), while
the response to rapid temperature changes is substantially lower. There is
no new minimum power floor, pulse-frequency increase, sensor filtering, or
relaxation of the temperature target.

The first adjustment reduced command variation but left a 2–3-minute hunt
near 1,030°C, with roughly 6–7°C of temperature ripple and occasional catch-up
waits. Derivative action had become small; proportional action still drove
large swings. The final adjustment reduces P and integral action by another
third, keeping the same integral time scale and derivative gain.

## Brief restart recovery

Previously, every service restart discarded the integral estimate of the power
needed to offset heat loss. At this temperature, that estimate is roughly
70–75 percentage points. Rebuilding it from zero caused a prolonged dip.

Automatic recovery now retains only that integral bias after a brief eligible
interruption. The saved state must be running with a ready sensor, matching
units/mode/profile, and no more than three control periods old. The saved PID
decision must be no more than two periods older than the saved state. Values
must be finite, the integral within 0–100, the saved output positive and at
most one, and the saved error within the PID window. A fresh sensor must show
temperature within one PID window of the saved reading and the current target,
and below the emergency limit. Future timestamps and malformed values are
rejected. Legacy or ineligible state follows the existing zero-bias recovery.

Only the integral is restored. Derivative history starts from the fresh error
and a nominal control period. Old output commands and timestamps are not
replayed, and ramp trim starts fresh. New firings never inherit the bias.
Normal PID, sensor shutdown, overtemperature cutoff, holds, and output bounds
continue to govern heating.

## Validation

Six response models fitted to recent readings had held-out one-step errors of
0.56–0.64°C and open-loop rollout errors of 1.49–2.30°C. Simulations exercise
the actual PID and ramp-control integration with 30-second on-then-off pulses,
unchanged catch-up rules, disturbances, reduced power, holds and the endpoint.
However, the models understated the live oscillation: closed-loop predictions
gave less than 1°C of ripple while subsequent observations still showed 6–7°C.
Replaying actual heater inputs predicted 5.4–7.1°C against 7.3°C observed, with
1.64–2.07°C temperature error. This supports the direction of gentler tuning,
but does not prove its live smoothness or model the median/relay phase effects
fully. Live observations determine acceptance.

Replaying the measured error sequence with 4/90/30 instead of 6/60/30 reduces
command standard deviation from 13.57 to 10.25 percentage points and raises
minimum requested power from 44.11% to 51.81%. These are counterfactual commands
on the same temperatures, not a prediction of the resulting temperature curve.
The largest reduction while colder than the catch-up tolerance is 7.45 points,
so gentler control can take longer to recover from a disturbance.

Fresh 736°C starts with zero integral remained stable in ten response models,
with final rates about 60°C/hour and similar overshoot, but 4/90/30 added about
132 seconds of initial catch-up on average (150 seconds worst paired case).
The active firing retains its recent bias and does not start from zero.
An intentionally excessive starting bias in lower-temperature models also
exposed larger startup overshoot. These are installation-specific checks,
not a universal kiln calibration. The recovery guard avoids carrying demand
through long or changed conditions.

The first staged release passed 352 Linux tests, including 78 cases for integral
recovery and 34 deployment-helper cases. Deployment ran from 16:12:55 to
16:13:26 UTC and preserved the active firing, original profile, saved program
position 50751.655850 seconds, history, elapsed origin, energy and cost.
Only the three PID gains changed in settings. After the fresh sensor window,
the first PID cycle used an integral of 72.7067 points versus 71.9240 saved,
with a derivative contribution of only 0.0233 points. The new source hash and
active settings were verified after recovery.

The refinement passed 361 Linux tests, including the recovery cases and 43
deployment-helper cases. It changed only the persisted gains at 16:30:11–
16:30:43 UTC; controller source remained identical. Recovery preserved the
same firing and its saved program position of 51624.233154 seconds. Integral
bias was 77.0703 points before and 77.3667 on the first fresh PID decision,
with a derivative contribution of 0.0234 points. The source, full settings,
profile files, history prefix and energy continuity were verified again.

## Live result

The read-only capture covered 16:04:39–16:12:52 UTC before tuning and
16:30:50–16:45:05 UTC with the final gains. The final observation contains 83
readings and 29 represented control cycles over 14 minutes 15 seconds,
including restart settling. Comparing the full observations avoids selecting
a favorable phase of the remaining oscillation.

| Measurement | Before | Final tuning |
| --- | ---: | ---: |
| Actual temperature trend | 52.10°C/hour | 57.92°C/hour |
| Target progression trend | 48.72°C/hour | 57.47°C/hour |
| Program progress between control decisions | 82.4% of wall time | 96.4% of wall time |
| Readings reporting catch-up | 18.0% | 3.6% |
| Heater command standard deviation | 28.65 percentage points | 8.12 percentage points |
| Heater command range | 21.5–100% | 61.7–90.6% |
| Longest commanded off interval | 23.55 seconds | 11.49 seconds |
| Middle-90% detrended temperature span | 9.34°C | 5.99°C |
| Largest observed drop over about ten seconds | 4.26°C | 2.54°C |

The final trace has one 30-second catch-up wait. Power variation fell about
72%, the longest off interval about 51%, and the detrended temperature span
about 36%. The actual and target trends differ by only 0.46°C/hour over the
full final observation, so these readings do not show sustained divergence.
The segment still requests 60°C/hour; its one wait reduces wall-clock progress.

Shorter fits vary with the oscillation and settling. For example, a ten-minute
actual-temperature fit moved from about 45°C/hour to 66°C/hour as its window
shifted, while the whole-episode trend stayed much closer to the target trend.
The final controller rate estimate, based on full sensor-window means, was
61.01°C/hour against 60 requested, with a +0.35-point power correction. That
single estimate does not demonstrate exact instantaneous rate tracking.

The controller and sensor stayed healthy, energy accounting remained monotonic,
and the firing origin and profile were unchanged. The post-refinement journal
had no warning, error or traceback through the final log capture. Temperature
ripple remains, and these observations establish improvement at this operating
point rather than universal tuning for every load. Earlier catch-up delays
remain in the elapsed history; the fix reduces additional lost program time.
