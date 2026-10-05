# Automatic ramp-speed correction

The controller can compare the measured temperature trend with the requested
rate of the current program segment and adjust heater duty to reduce a sustained
difference. Enable **Settings → Firing → Automatically correct ramp speed**.
The repository default is off; the Orange Pi installation enables it in its
persisted settings.

The dashboard's **Ramp tracking** panel shows the current segment rate, measured
rate, and the power adjustment actually applied, in percentage points. A +2 pp
adjustment changes a 60% heating command to 62%. Positive adjustment adds heat;
on a cooling segment, it slows cooling. The panel distinguishes collecting or
confirming readings, tracking, correction, temperature priority, and power or
correction limits. Disconnected readings are marked as last reported.

## Measurement and correction

- One observation is taken per control cycle, using the mean of the raw sensor
  window. The existing median temperature remains the PID and safety input.
- A linear trend is fitted to the latest ten minutes, with at least five minutes
  and six observations required. Monotonic elapsed time is used even while
  catch-up freezes the program clock. Browser polling cannot change the rate.
- The rate is checked every minute. Error must exceed the larger of 3°C/hour,
  8% of the requested rate, or 1.5 times the trend's standard error, and persist
  across two checks. Fahrenheit thresholds scale equivalently.
- Learned duty correction changes by at most two percentage points per check,
  bounded to ±10 points. A blocked correction may be removed immediately so it
  cannot override a temperature or power limit.
- A new segment, pause/resume, disable/enable, restart, clock reversal, sensor
  fault, or sampling gap longer than 90 seconds clears learned correction and
  starts a fresh measurement window. Holds and pauses use ordinary temperature
  control with zero rate adjustment.

The temperature target remains authoritative. A correction cannot increase an
existing excess beyond the catch-up tolerance, deepen a temperature deficit,
override the PID's full-on/off decisions, exceed the heating limit, or introduce
active cooling. The existing PID gains are unchanged. Integral accumulation is
held only when an applied correction causes actuator saturation in that direction.

The Orange Pi retains its 30-second relay cycle, ten sensor samples per cycle,
independent 2.7778°C catch-up tolerance, sensor shutdown, overtemperature cutoff,
and the original saved program. Neither schedule points nor historical readings
are rewritten. Correction follows the segment's slope; it does not accelerate
the schedule to erase time already lost. The planned and actual chart lines can
therefore remain separated after the slope improves.

## Diagnostics and validation

`GET /api/health` and status WebSocket messages include `ramp_control`: requested
and measured rates (configured temperature units/hour), deadband, window length,
next-check time, learned/applied trim, actual output, and correction count.
`pidstats.base_out` is the temperature PID duty, `pidstats.out` is final duty,
and `pidstats.ramp_trim` is the applied difference in percentage points. Relay
on-time and energy accounting use the final command and actual energized time.
Controller logs report applied corrections. Learning is intentionally not saved
across a restart; the setting itself persists.

Pure regression and integration tests exercise timing, signed heating/cooling
feedback, unit conversion, noise, limits, actual pulse/energy accounting, holds,
recovery and shutdown. Browser fixtures exercise the panel and existing graphs.
220 simulations using the actual PID and integration code preserved program data,
output bounds, and holds. They added no catch-up time versus baseline in the
tested scenarios; three disturbed-heating cases saved 30 seconds. The largest
additional modeled overshoot was 0.125°C. These fitted models approximate the
recorded response around 736–855°C and do not establish performance at every
temperature or load. Live measurements remain the check on actual performance.

Matching a ramp exactly is not guaranteed: heating capacity, passive cooling,
temperature waits, measurement noise and the bounded correction can limit it.
The panel exposes those conditions rather than altering the planned graph.

## Orange Pi deployment — 5 October 2026

The release passed 268 Linux tests in an isolated staged directory, including
injected deployment-write failures and rollback of a previously absent module.
46 browser fixture groups passed across the ramp panel, comparison graph,
warm-start alignment and zoom. The running page was also checked at desktop and
mobile widths, with no browser errors or control writes.

Deployment started at 13:52:08 UTC and recovered at 13:52:40 UTC. The same firing
(`1791195985736-aa30cae285`) resumed from saved program position 43303.764470
seconds without seeking to a new temperature. Its original elapsed origin,
program, recorded history, accumulated energy and cost were preserved and checked.
The only settings change was `automatic_ramp_control: true`; source hashes and
active settings were verified after recovery. The controller began a fresh
measurement window for the 61.7647°C/hour segment toward 950°C.

Live feedback first assessed the rate after 300.27 seconds and reported
`confirming`. At 13:58:40 UTC, after the next minute's check, it detected a
9.324°C/hour trend versus 61.7647 requested and applied +1.6981 percentage points:
the temperature PID requested 64.2384% duty and the final command was 65.9365%.
The following control cycle retained that correction without adding another;
its next check was still 30 seconds away. The initial window includes the
temperature dip and catch-up after restarting, so it is not a settled-rate
performance measurement.

The observation captured 72 readings across 25 control cycles. Five successive
minute checks increased trim to +5.6181 points; later checks held it steady as
the rate entered the uncertainty band. At 14:04:46 UTC, temperature was 901.58°C
against a 900.85°C target. The controller's ten-minute cycle-mean trend was
58.97°C/hour versus 61.76 requested (deadband 9.37°C/hour). An independent fit
of the saved median temperature readings over 9m53s was 62.41°C/hour. All
reported final duties matched base duty plus applied trim, and energy/cost
remained monotonic. No sensor or controller fault occurred.

Catch-up occupied 40% of that ten-minute observation window, mostly during
recovery; target advancement averaged 37.20°C/hour over the same interval.
Thus the close temperature slope confirms the current trend, not an exact
finish time or recovery of earlier lost program time. Automatic correction
remains active on subsequent segments, with fresh measurements at each change.
