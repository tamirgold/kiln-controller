# API and diagnostics

The controller serves its browser interface and API from the same HTTP port.
The examples below run on the controller itself at `http://127.0.0.1:8081`.
When connecting from another device, use the controller's local hostname or IP
address and configured port.

The API has no user authentication or TLS. Keep it on a trusted local network
and do not expose its port directly to the Internet. Review tokens and revision
checks protect certain multi-step edits; they are not authentication.

## Routes

| Interface | Purpose |
| --- | --- |
| `GET /api/health` | Current state, sensor readiness, energy and controller liveness |
| `GET /api/stats` | PID statistics |
| `POST /api` | `run`, `stop`, `pause`, `resume`, `memo` or `stats` command |
| `GET /api/firings` | Firing records and aggregate statistics |
| `GET /api/firings/<id>` | Individual record and samples as JSON |
| `GET /api/firings/<id>?format=csv` | Individual samples as CSV |
| `POST /api/firings/clear` | Confirmed clearing of reviewed ended records |
| `GET /api/settings` | Read settings |
| `POST /api/settings` | Save pending settings |
| `POST /api/settings/discard` | Discard pending settings |
| `POST /api/settings/apply` | Apply settings and restart |
| WebSockets `/status`, `/config`, `/storage`, `/control` | Live updates, display configuration, program storage and legacy control |

Settings/history mutations require their current review token and revision.
Use the [Settings](SETTINGS.md) and [History](USER-GUIDE.md#firing-history)
review workflows when operating the controller manually. Saving settings does
not change an active firing; apply requires an idle kiln with no eligible
recovery waiting. History clearing removes reviewed ended firings while
preserving saved programs and running/paused firings.

## Read status

```bash
curl --fail http://127.0.0.1:8081/api/health
curl --fail http://127.0.0.1:8081/api/stats
```

Firing history can be exported with the routes above. Replace `<id>` with a
record's actual ID. History CSV temperatures are Celsius regardless of the
interface's display units. Real and simulated firings have separate archives.

## Send a command

`POST /api` accepts JSON with a `cmd` field. The examples send real commands
to the selected controller. Explore them in the documented
[simulation preview](GETTING-STARTED.md) before using them with a commissioned
kiln, using the preview's port in each URL.

### Start a saved program

Replace `my-program` with the name of an existing saved program.

```bash
curl --fail -H 'Content-Type: application/json' \
  -d '{"cmd":"run","profile":"my-program"}' \
  http://127.0.0.1:8081/api
```

### Start at a specified program time

`startat` is in **minutes**, not seconds. A positive value bypasses warm-start
seek. This example starts at minute 60 of the saved schedule.

```bash
curl --fail -H 'Content-Type: application/json' \
  -d '{"cmd":"run","profile":"my-program","startat":60}' \
  http://127.0.0.1:8081/api
```

### Stop a firing

Stop switches the heat request off and cancels automatic recovery of that
firing. It is not electrical isolation. Stopping or restarting the service
has different recovery behavior; see [control and recovery](CONTROL.md).

```bash
curl --fail -H 'Content-Type: application/json' \
  -d '{"cmd":"stop"}' \
  http://127.0.0.1:8081/api
```

### Add a memo

```bash
curl --fail -H 'Content-Type: application/json' \
  -d '{"cmd":"memo","memo":"Recorded a firing observation"}' \
  http://127.0.0.1:8081/api
```

### Pause and resume

**Pause maintains temperature and can continue heating.** It does not switch
the kiln off. Pause/resume are API commands, not dashboard buttons. A paused
record is not eligible for automatic power-loss recovery.

```bash
curl --fail -H 'Content-Type: application/json' \
  -d '{"cmd":"pause"}' \
  http://127.0.0.1:8081/api
```

```bash
curl --fail -H 'Content-Type: application/json' \
  -d '{"cmd":"resume"}' \
  http://127.0.0.1:8081/api
```

## PID diagnostics

Open `/state` on the controller for the
[diagnostics view](../public/state.html). It plots temperature, error, duty and
PID terms, and offers a CSV dump. Its plotting/table libraries load from cdnjs;
the dashboard, history and settings assets are served locally.

Additional tools include [PID autotuning](ziegler_tuning.md),
[manual tuning notes](pid_tuning.md), the separately configured
[Slack watcher](watcher.md) and [OS-based scheduling with at](schedule.md).
They are separate tools, not dashboard features. Review scripts and dated
examples before use; sensor/output tests and autotuning can access real hardware.
