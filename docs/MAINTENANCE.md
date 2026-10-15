# Data, backups and maintenance

Keep a copy of the controller's local settings, programs and firing history
before updating. Git tracks the application source; it is not a backup of the
installation's runtime data.

Use the matching [build guide](GETTING-STARTED.md) for installation. The current
[Orange Pi guide](INSTALL.md) contains the detailed backup/update commands;
the [Raspberry Pi guide](builds/raspberry-pi.md) identifies its board requirements.

## Files to preserve

| Default path | Contents |
| --- | --- |
| `config.py` | Tracked base configuration; preserve any deliberate local source changes separately |
| `settings.json`, `settings.pending.json` | Applied local overrides and saved pending changes |
| `storage/settings-backups/` | Settings snapshot saved before each apply |
| `storage/profiles/` | Saved program JSON files, including explicit temperature units |
| `state.json` | Atomic recovery state and last firing totals when saved |
| `storage/firings/` | Real firing records, `samples.jsonl` and per-firing summaries |
| `storage/simulated-firings/` | Separate simulated records and summaries |

Back up local settings, recovery state and **all of `storage/`**. Settings can
relocate the recovery file and program directory; include those actual paths
if they differ. Keep the service configuration and selected board profile with
your installation notes so a replacement device uses the same configuration.

Firing samples are normally saved every ten seconds. Summaries refresh
periodically and at important transitions. The dashboard can down-sample long
curves for display while history retains its saved samples.

For individual records, use the JSON/CSV exports in
[firing history](USER-GUIDE.md#firing-history). Exporting one record does not
replace a complete backup of settings, programs and recovery data.

## Configuration sources

The selected hardware profile supplies the board's pin defaults. `config.py`
supplies base settings, and `settings.json` contains the applied local overrides.
Saving through the interface creates `settings.pending.json`; pending changes
are not active until they are applied while idle. See the
[settings workflow](SETTINGS.md#save-and-apply-changes).

| Environment variable | Purpose |
| --- | --- |
| `KILN_BOARD` | Select `orange-pi-zero-2w` or `raspberry-pi`; an omitted profile preserves the Orange Pi legacy choice |
| `KILN_SETTINGS_FILE` | Select the applied local settings file |
| `KILN_STATE_FILE` | Override the recovery state path |
| `KILN_PORT` | Override the HTTP port |
| `KILN_SIMULATE` | Select simulation/real mode; `1` selects simulation |

Environment-selected mode, port and recovery path are locked in Settings.
The board profile must match the physical board and its wiring; switching it
does not rewire a controller or validate another board's support. Consult the
[board compatibility guide](supported-boards.md) before changing hardware.

Use an isolated settings path, recovery file and port when following a preview
or test procedure. A separate recovery file prevents a preview from replacing
a real firing's saved progress.

## Back up and update

1. Wait until the kiln is idle. If you need to end a firing, use **Stop firing**;
   stopping the service during a firing preserves recovery state and may allow
   automatic resumption.
2. Follow the [backup and update procedure](INSTALL.md#8-back-up-and-update)
   using your installation's account, repository directory and service setup.
   Preserve the files above before fetching or applying changes.
3. Review local source changes and any new dependency, service or board-profile
   requirements. Do not discard local changes to make an update succeed.
4. Run the documented checks, restart the service when ready, and confirm the
   expected mode, settings, sensor status and idle state in the dashboard.

For a new board or an altered driver, repeat the relevant commissioning checks
from the [hardware guide](HARDWARE.md#6-check-in-this-order). Software tests do
not verify physical wiring, temperature calibration, output polarity or kiln
tuning.

## Routine checks and troubleshooting

The [installation guide](INSTALL.md#7-recovery-tests-and-routine-checks) explains
how to inspect service logs, check Chrony synchronization and read
`/api/health`. The health endpoint reports current state, sensor readiness,
energy and controller liveness; see the [API guide](api.md).

Confirm fresh, plausible sensor readings and the expected mode before starting
a firing. If a browser disconnects, the controller keeps operating; reconnect
to inspect its state rather than assuming that the firing stopped.

For software checks, use the dependency environment described in the build or
development guide and an isolated settings path. On a Linux installation with
the project virtual environment:

```bash
kiln_test_dir="$(mktemp -d)"
KILN_SIMULATE=1 KILN_SETTINGS_FILE="$kiln_test_dir/settings.json" \
  venv/bin/python -m pytest -q Test
```

Tests cover program interpolation, recovery, energy accounting, staged settings
and firing history. They do not replace hardware commissioning. Use
[development instructions](DEVELOPMENT.md) for the current test environment and
[troubleshooting](troubleshooting.md) for additional diagnostic notes. Review
older examples against the current build guide before copying commands.
