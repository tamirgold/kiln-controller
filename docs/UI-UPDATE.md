# Dashboard update — 23 September 2026

> Historical deployment record from September 2026. Deployment-specific settings,
> firing history, and verification screenshots remain local and are not included
> in this repository. The tracked source defaults use `gpio_heat_invert=False`
> and a two-second control cycle; the documented deployment uses active-low
> output and a 30-second cycle through local settings overrides. These notes
> describe past deployments, not the current source defaults.

Installed at http://orangepizero2w.local:8081/picoreflow/index.html?ui=20260923
(IP fallback: http://192.168.68.54:8081/picoreflow/index.html?ui=20260923).

- Responsive dashboard tested at 320, 390, 768 and 1440 pixels.
- Actual elapsed firing time in hours, minutes and seconds; independent of program progress, pauses and catch-up periods. Saved across automatic recovery, including times longer than 24 hours.
- Current `test-fast` firing retains its journal-confirmed original start, 2026-09-23 11:24:40.633 UTC / 14:24:40.633 Israel time.
- Program and recent 30-minute graphs, measured/target curves, tooltips, keyboard inspection and CSV export of available readings. The later history update below adds persistent readings across restarts.
- Heater duty, estimated requested kW, actual temperature rate, program progress, remaining program time, sensor and connection status.
- Program editor with Celsius targets, cumulative minutes, calculated ramp rates, validation and confirmation for start/stop/delete. Active firings retain their original embedded schedule.
- Installed power 11.0 kW, tariff ₪0.645/kWh, recovery within 15 minutes and configured temperature limit are displayed.

Validation: 28 Python tests passed. Simulation browser checks exercised program creation/edit/delete, Hebrew names, invalid times, start/stop, graph inspection/export, 49-hour recovery and disconnection. Live read-only browser verification confirmed the running program, original elapsed time, healthy sensor, configuration values and responsive layouts; no browser errors.

Deployment completed 2026-09-23 14:35:40 UTC with one brief service restart and verified automatic recovery at the saved program position. Configuration and all user profiles were verified unchanged. `kiln-controller.service` remains active and enabled at startup. The separate simulation service was stopped after testing.

Remote backup: `/home/orangepi/kiln-backups/dashboard-20260923T143535Z`, including previous files, configuration, profiles, saved state and before/after health records. Do not restore an old RUNNING state after an intentional stop.

Verification screenshots remain local. If an already-open browser shows the previous interface, refresh it or use the versioned URL above.

## Firing electricity cost — 15:07 UTC update

The dashboard now displays estimated firing cost, kWh and heater on-time. With the current configuration, cost is on-seconds / 3600 × 11 kW × ₪0.645/kWh. New accounting measures the SSR control signal's on-duration using a monotonic clock, including partial pulses, catch-up and paused heating. Off-time adds zero. These are rated-power estimates, not readings from an electricity meter.

The totals persist with automatic recovery. The final total remains visible after stop/completion, including after a service restart, and a new firing starts from zero. Old pulse-count-based cost values are not reused.

The active firing's earlier on-time was reconstructed from 4,823 heater-cycle log entries. Missing cycles were estimated from neighboring duty values within each service run, excluding service downtime. The dashboard labels this historical estimate. A future legacy state without usable energy history is explicitly shown as a partial total.

Validation: 37 Python tests passed, including fractional duty, repeated polling, heater-off periods, a one-hour cost of ₪7.095, partial-pulse stop, recovery and final-cost retention. A separate reconstruction check verifies missing cycles and service downtime. Browser checks passed at 320–1440 pixels, after simulated completion and against the live firing; no browser errors. Live cost increments matched 11 × 0.645 × on-seconds / 3600.

The real firing resumed at the saved program position with its original elapsed timer preserved. Configuration and user profiles were unchanged. Remote backup: `/home/orangepi/kiln-backups/cost-20260923T150718Z`, including the source heater logs and reconstruction details.

Updated URL: http://orangepizero2w.local:8081/picoreflow/index.html?ui=20260923-cost-1


## Settings page — 15:29 UTC update

URL: http://orangepizero2w.local:8081/picoreflow/settings.html

All 59 configuration values are visible; 56 active values are editable and three unused compatibility values are read-only. Categories include electricity/display, firing behavior, PID, thermocouple and physical header pins, recovery, protection overrides, server/storage and simulation. Search, technical names, export and a review of changes are included.

Review & save creates a pending draft. Apply & restart is available only while idle with no automatic recovery pending. Pending settings are never loaded during firing recovery. Values, pins, units, paths and ports are validated, and stale browser edits are rejected. Active configuration backups are retained in storage/settings-backups. Celsius/Fahrenheit changes convert temperature settings and PID parameters; stored programs load in the selected units. Completed firing costs keep their original power and tariff.

Backup: /home/orangepi/kiln-backups/settings-20260923T152944Z. Original active values, current firing progress and user profiles were preserved. Verification included 70 Python tests, real browser checks, settings apply/reconnect, pending drafts across a simulated firing restart, stale confirmation rejection and 320–1440 px layouts.

## Firing history, statistics and ramp guidance — 15:51 UTC update

URL: http://orangepizero2w.local:8081/picoreflow/history.html
Dashboard: http://orangepizero2w.local:8081/picoreflow/index.html?ui=20260923-history-1

The controller saves a snapshot of each firing's program, its original start, configuration of power/tariff, temperature and actual target readings, elapsed and program time, heater on-time, energy, cost, sensor readiness and catch-up state. Samples are appended and synced every 10 seconds, with immediate checkpoints at start, service shutdown and completion/stop. A restored firing retains its identity. Interrupted records are closed when recovery is no longer possible. A truncated final append does not destroy earlier or subsequent samples. Disk errors appear on the dashboard.

Records live under /home/orangepi/kiln-controller/storage/firings/<firing-id>/:
- samples.jsonl: durable raw readings in Celsius with seconds and UTC epoch timestamps.
- record.json: embedded program, firing status, original cost parameters and computed statistics.
- ../averages.json: all record summaries and aggregate statistics, refreshed each minute and at firing end.

These files persist across restarts and are not automatically deleted. Simulation uses a separate simulated-firings directory. Export an individual firing as JSON or CSV, or export all summary statistics from the history page.

Per-firing statistics include elapsed time, peak/mean temperature, mean target error, observed duration, catch-up and pause time, heater on-time, kWh, cost, data gaps, and measured ramp rates. The page shows averages across ended firings (including stopped/interrupted runs); in-progress firings are excluded until they end. Currency totals and averages remain separate. Unknown data is not treated as zero, and partial/estimated history is marked.

Ramp guidance uses the fastest sustained three-minute temperature rise within each 50°C band, with at least 90% heater duty and a linear fit of R² ≥ 0.9. It excludes cooling, holds, invalid sensors, service boundaries and gaps over 30 seconds. Rates are based on wall-clock time, not catch-up-stalled program time. Available observations at the current power rating are combined; unmeasured ranges are explicitly unknown. They are measured guidance, not guaranteed physical limits: kiln load and conditions can change performance.

The program editor now accepts a rate directly, adjusts that segment's duration, and shifts later points while preserving their durations. It warns if a heating segment exceeds the recorded maximum in any measured temperature band it crosses. Users can still save the chosen rate. Celsius/Fahrenheit and hour/minute/second settings are respected. Cooling rates use negative values; hold duration is set using time.

Graph tooltips show hours and minutes and temperature, with measured/target labels. Future program points are also inspectable. The dashboard reloads saved readings and the history page plots the entire recorded firing. Saved raw files retain the full history even when the dashboard reduces the number of drawn points.

Recovered 1,346 initial samples for the active test-fast firing, starting from the surviving 31°C reading near its original 2026-09-23 11:24:40.633 UTC start. Eight temperature bands had qualifying measurements at deployment. Only recorded temperatures were imported; gaps remain visible. Earlier energy use retains its existing log-based estimate.

Backup: /home/orangepi/kiln-backups/history-20260923T155122Z, including previous software, profiles, state, settings draft, source journal and import results. The firing resumed with original elapsed origin and profile, program position 6724.247 seconds, cost ₪14.916875 and healthy 524.56°C sensor. Original active configuration and profiles were verified unchanged.

A user-created pending settings draft was preserved during deployment, including 5.5 kW and a 25-minute recovery window. At deployment the running values remained 11 kW, ₪0.645/kWh, Celsius and 15-minute recovery. The draft must be applied while idle through Settings; deployment did not apply it.

Validation: 89 Python tests passed. Browser tests verified editable rates, warnings and allowed saves, schedule point and recorded point tooltips, CSV/JSON exports, Fahrenheit and Celsius, and layouts from 320 to 1440 px. A simulated service restart preserved one firing record; both stop and automatic completion saved final statistics. Live read-only checks verified healthy firing, restored history, original elapsed origin, no browser errors and increasing durable samples. The simulation service was stopped after testing; the real service remains active and enabled.

Verification screenshots for the history and dashboard layouts remain local.


## Mechanical relay interface — 24 September 2026, 08:16 UTC

After confirmation of mains isolation and successful low-trigger testing,
physical pin 37 was configured active-low (gpio_heat_invert=True). The mechanical
relay switches the SSR's 5 V DC control input. The cycle is now 30 seconds
(sensor_time_wait=30). A watcher change keeps status updates every two seconds,
so the dashboard stays connected and firing history keeps its normal cadence.

The current firing was stopped before applying these changes. Its final history
and bill were retained, and it will not resume automatically. Verified after
restart: IDLE, heat=0, pin 37 OUTPUT HIGH, service enabled, live status about
2.00 seconds apart, thermocouple approximately 133 C. The earlier 0 C reading
cleared after restart; physical temperature agreement still needs user verification.

Mock GPIO tests passed for both output polarities. A separate watcher test with
a 30-second control interval and a live websocket check verified responsive
status. Other pending settings were preserved; the older five-second draft
cycle was rebased to 30 seconds. See RELAY-MODULE-CHANGE.md for wiring and details.
Backup: /home/orangepi/kiln-backups/relay-20260924T081623Z.

## Clear firing history — 24 September 2026, 09:41 UTC

The firing history page now has a Clear history button beside Export statistics.
It fetches a fresh count and requires confirmation before deleting finished
records and their saved readings. Running and paused firings, programs, settings
and recovery state are preserved. Averages and learned ramp rates are recalculated
from the remaining records. The button is disabled when there are no finished runs.

The API rejects missing tokens, cross-origin requests and stale confirmations.
Deletion and archive capture share a lock. Deleted directories are moved out of
the startup discovery path before removal, with interrupted cleanup completed
on restart. Tests cover partial filesystem failure and unsafe storage paths.

Validation: 97 Python tests passed. Browser tests on simulation port 8082 verified
Cancel, stale confirmation, deletion during an active firing, clearing the last
record, reset statistics, persistence across service restart, and layouts at
320/390/1440 pixels. All test run/stop/delete requests were restricted to simulation.

Deployment preserved all 18 real records byte-for-byte, current settings and
programs, with the controller idle and pin 37 HIGH/OFF after restart. The user had
applied settings before deployment (8 kW, 25-minute recovery, active-low output,
30-second cycle); these were retained. Service startup remains enabled.

Backup: /home/orangepi/kiln-backups/history-clear-20260924T094123Z, including the
previous code, all 18 firing records, programs, state and settings.

After deployment, a browser submitted a successful clear request at 09:42:32 UTC
and started a new 1250 instant firing at 09:42:47 UTC. This was outside the live
read-only validation. The earlier records remain in the deployment backup.
The simulation service was stopped after testing.
