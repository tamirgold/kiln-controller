"""Durable firing records and empirical, sustained ramp measurements.

Temperatures are stored in Celsius and time is always wall-clock seconds.
Program time may stop during catch-up; it must never be used for ramp rates.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import statistics
import tempfile
import threading
import time
import uuid


ACTIVE = ('RUNNING', 'PAUSED')
SAMPLE_SECONDS = 10
BAND_C = 50
WINDOW_SECONDS = 180


class HistoryChanged(ValueError):
    pass


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def celsius(value, scale):
    return (value - 32) * 5 / 9 if scale == 'f' else value


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.history-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def firing_id(state):
    origin = state.get('run_started_at')
    if not number(origin) or origin <= 0:
        return None
    identity = json.dumps([origin, state.get('profile'), bool(state.get('simulate'))])
    return str(int(origin * 1000)) + '-' + hashlib.sha256(identity.encode()).hexdigest()[:10]


def sample(state, scale, session):
    energy = state.get('energy_accounting') or {}
    ready = state.get('sensor_ready') is not False
    def temp(key):
        v = state.get(key)
        return celsius(v, scale) if ready and number(v) else None
    duty = (state.get('pidstats') or {}).get('out')
    return dict(timestamp=state['timestamp'], elapsed_seconds=state.get('elapsed_seconds', 0),
                program_seconds=state.get('runtime', 0), temperature_c=temp('temperature'),
                target_c=temp('target'), sensor_ready=ready, state=state['state'],
                catching_up=bool(state.get('catching_up')), session=session,
                heater_on_seconds=energy.get('heater_on_seconds'), energy_kwh=energy.get('energy_kwh'),
                cost=energy.get('cost'), duty=max(0, min(1, duty)) if number(duty) else None)


def continuous(a, b):
    return (0 < b['timestamp'] - a['timestamp'] <= 30 and a['session'] == b['session']
            and a.get('sensor_ready') and b.get('sensor_ready')
            and number(a.get('temperature_c')) and number(b.get('temperature_c')))


def summarize(points, meta):
    valid = [p for p in points if number(p.get('temperature_c')) and p.get('sensor_ready')]
    seconds = temp_area = error_area = error_seconds = catchup = paused = 0.0
    gaps = 0
    for a, b in zip(points, points[1:]):
        if not continuous(a, b):
            gaps += 1
            continue
        dt = b['timestamp'] - a['timestamp']
        seconds += dt
        temp_area += (a['temperature_c'] + b['temperature_c']) / 2 * dt
        if all(number(p.get('target_c')) for p in (a, b)):
            error_area += (abs(a['temperature_c'] - a['target_c']) + abs(b['temperature_c'] - b['target_c'])) / 2 * dt
            error_seconds += dt
        catchup += dt if a.get('catching_up') else 0
        paused += dt if a['state'] == 'PAUSED' else 0
    end = meta.get('finished_at') or (points[-1]['timestamp'] if points else meta['started_at'])
    energy = meta.get('energy') or {}
    result = dict(sample_count=len(points), elapsed_seconds=max(0, end - meta['started_at']),
                  observed_seconds=seconds, peak_temperature_c=max((p['temperature_c'] for p in valid), default=None),
                  mean_temperature_c=temp_area / seconds if seconds else None,
                  mean_tracking_error_c=error_area / error_seconds if error_seconds else None,
                  catchup_seconds=catchup, paused_seconds=paused, gaps=gaps,
                  partial=bool(not points or points[0]['elapsed_seconds'] > 30 or gaps),
                  heater_on_seconds=energy.get('heater_on_seconds'), energy_kwh=energy.get('energy_kwh'),
                  cost=energy.get('cost'), currency_type=energy.get('currency_type', meta.get('currency_type', '')),
                  energy_estimated=bool(energy.get('history_estimated')),
                  energy_incomplete=bool(energy.get('history_incomplete')), ramps=[])
    # Non-overlapping three-minute windows: enough to smooth thermocouple noise
    # and avoid counting hundreds of overlapping windows as independent evidence.
    window = []
    bands = {}
    for p in points:
        if not p.get('sensor_ready') or not number(p.get('temperature_c')) or p['state'] != 'RUNNING':
            window = []
            continue
        if window and not continuous(window[-1], p):
            window = []
        window.append(p)
        elapsed = p['timestamp'] - window[0]['timestamp']
        if elapsed < WINDOW_SECONDS:
            continue
        w = window
        window = [p]
        if elapsed > 210 or len(w) < 8:
            continue
        lo, hi = min(q['temperature_c'] for q in w), max(q['temperature_c'] for q in w)
        band = math.floor(lo / BAND_C) * BAND_C
        if hi > band + BAND_C or hi - lo < 3:
            continue
        on = [q.get('heater_on_seconds') for q in (w[0], w[-1])]
        if all(number(v) for v in on):
            duty = (on[1] - on[0]) / elapsed
        else:
            # Imported cycle logs have actual pulse duty but no cumulative meter.
            duties = [q.get('duty') for q in w]
            duty = statistics.mean(duties) if all(number(v) for v in duties) else 0
        if not .9 <= duty <= 1.1:
            continue
        xs = [q['timestamp'] - w[0]['timestamp'] for q in w]
        ys = [q['temperature_c'] for q in w]
        xm, ym = statistics.mean(xs), statistics.mean(ys)
        slope = sum((x-xm)*(y-ym) for x, y in zip(xs, ys)) / sum((x-xm)**2 for x in xs)
        variance = sum((y-ym)**2 for y in ys)
        r2 = 1 - sum((y-ym-slope*(x-xm))**2 for x, y in zip(xs, ys)) / variance if variance else 0
        if slope <= 0 or r2 < .9:
            continue
        bands.setdefault(band, []).append(slope * 3600)
    result['ramps'] = [dict(from_c=b, to_c=b+BAND_C, max_rate_c_hour=max(rates),
                            mean_rate_c_hour=statistics.mean(rates), windows=len(rates))
                       for b, rates in sorted(bands.items())]
    return result


def aggregate(records, power):
    ended = [r for r in records if r['status'] not in ACTIVE]
    def average(key):
        values = [r['stats'].get(key) for r in ended if number(r['stats'].get(key))]
        return dict(value=statistics.mean(values) if values else None, count=len(values))
    costs = {}
    for r in ended:
        s = r['stats']
        if number(s.get('cost')):
            costs.setdefault(s['currency_type'], []).append(s['cost'])
    bands = {}
    for r in records:
        if abs(r.get('kw_elements', 0) - power) > .01:
            continue
        for b in r['stats'].get('ramps', []):
            item = bands.setdefault(b['from_c'], dict(from_c=b['from_c'], to_c=b['to_c'],
                max_rate_c_hour=0, mean_rate_c_hour=0, windows=0, firing_count=0))
            item['max_rate_c_hour'] = max(item['max_rate_c_hour'], b['max_rate_c_hour'])
            item['mean_rate_c_hour'] += b['mean_rate_c_hour'] * b['windows']
            item['windows'] += b['windows']
            item['firing_count'] += 1
    for b in bands.values():
        b['mean_rate_c_hour'] /= b['windows']
    return dict(firing_count=len(records), finished_count=len(ended), active_count=len(records)-len(ended),
                completed_count=sum(r['status'] == 'completed' for r in ended),
                averages={key:average(key) for key in ('elapsed_seconds','energy_kwh','heater_on_seconds',
                    'peak_temperature_c','mean_temperature_c','mean_tracking_error_c','catchup_seconds')},
                costs=[dict(currency_type=k, total=sum(v), average=statistics.mean(v), count=len(v)) for k,v in costs.items()],
                ramps=sorted(bands.values(), key=lambda b:b['from_c']), kw_elements=power,
                band_c=BAND_C, window_seconds=WINDOW_SECONDS,
                method='Fastest sustained 3-minute rise at ≥90% heater duty, within each 50°C band. Measured guidance, not a guaranteed limit.')


class Archive:
    def __init__(self, root, config):
        self.root = Path(root)
        self.config = config
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.session = uuid.uuid4().hex
        self.records = {}
        self.current_id = None
        self.current_points = []
        self.last_summary = 0
        self.error = None
        # Finish removing records already cleared before a process or power interruption.
        for path in self.root.glob('.clear-*'):
            if re.fullmatch(r'\.clear-[a-z0-9_]{8}', path.name) and not path.is_symlink():
                try:
                    shutil.rmtree(path)
                except OSError:
                    self.error = 'Some previously cleared history files could not be removed.'
        for path in self.root.glob('*/record.json'):
            try:
                r = json.loads(path.read_text())
                if re.fullmatch(r'\d+-[a-f0-9]{10}', r['id']):
                    self.records[r['id']] = r
            except (ValueError, KeyError, OSError):
                self.error = 'An older firing record could not be read.'

    def read_points(self, identity):
        if identity not in self.records:
            raise KeyError(identity)
        points = []
        path = self.root / identity / 'samples.jsonl'
        if path.exists():
            with path.open() as f:
                for line in f:
                    try:
                        p = json.loads(line)
                        if number(p.get('timestamp')) and (not points or p['timestamp'] > points[-1]['timestamp']):
                            points.append(p)
                    except ValueError:
                        # A power cut may truncate the last append; older rows survive.
                        continue
        return points

    def _flush(self, identity, points):
        meta = self.records[identity]
        meta['stats'] = summarize(points, meta)
        atomic_json(self.root / identity / 'record.json', meta)
        atomic_json(self.root / 'averages.json', self.overview())
        self.last_summary = time.monotonic()

    def capture(self, state, force=False, finish=None):
        if state.get('state') not in ACTIVE:
            return
        identity = firing_id(state)
        if not identity:
            return
        with self.lock:
            if identity not in self.records:
                profile = json.loads(json.dumps(state['profile_data']))
                profile['data'] = [[t,celsius(v,self.config.temp_scale)] for t,v in profile['data']]
                profile['temp_units'] = 'c'
                self.records[identity] = dict(version=1, id=identity, profile=state['profile'],
                    profile_data=profile, started_at=state['run_started_at'], status=state['state'],
                    finished_at=None, simulate=bool(state.get('simulate')), kw_elements=self.config.kw_elements,
                    kwh_rate=self.config.kwh_rate, currency_type=self.config.currency_type,
                    original_temp_scale=self.config.temp_scale, stats={}, energy={})
                directory = self.root / identity
                directory.mkdir(parents=True, exist_ok=True)
                atomic_json(directory / 'record.json', self.records[identity])
            if self.current_id != identity:
                self.current_id = identity
                self.current_points = self.read_points(identity)
            points = self.current_points
            if points and state['timestamp'] <= points[-1]['timestamp']:
                return
            if points and not force and not finish and state['timestamp'] - points[-1]['timestamp'] < SAMPLE_SECONDS:
                return
            row = sample(state, self.config.temp_scale, self.session)
            # Leading newline isolates any incomplete append left by a power cut.
            with (self.root / identity / 'samples.jsonl').open('a', encoding='utf-8') as f:
                f.write('\n' + json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
                f.flush()
                os.fsync(f.fileno())
            points.append(row)
            meta = self.records[identity]
            meta['energy'] = state.get('energy_accounting') or {}
            meta['status'] = finish or state['state']
            if finish:
                meta['finished_at'] = state['timestamp']
            if force or finish or time.monotonic()-self.last_summary >= 60 or len(points) == 1:
                self._flush(identity, points)

    def reconcile_idle(self):
        """Called only when automatic recovery is no longer possible."""
        with self.lock:
            for identity, meta in self.records.items():
                if meta['status'] in ACTIVE:
                    points = self.read_points(identity)
                    if points:
                        for key in ('heater_on_seconds', 'energy_kwh', 'cost'):
                            if number(points[-1].get(key)):
                                meta['energy'][key] = points[-1][key]
                    meta['status'] = 'interrupted'
                    meta['finished_at'] = points[-1]['timestamp'] if points else meta['started_at']
                    self._flush(identity, points)

    def overview(self):
        with self.lock:
            records = [r for r in self.records.values() if r['simulate'] == self.config.simulate]
            return dict(updated_at=time.time(), records=sorted(records, key=lambda r:r['started_at'], reverse=True),
                        summary=aggregate(records, self.config.kw_elements), error=self.error,
                        temp_scale=self.config.temp_scale, simulate=self.config.simulate)

    def clear_review(self):
        with self.lock:
            identities = sorted(r['id'] for r in self.records.values()
                                if r['simulate'] == self.config.simulate and r['status'] not in ACTIVE)
            revision = hashlib.sha256(json.dumps(identities).encode()).hexdigest()
            return dict(count=len(identities), revision=revision)

    def clear_finished(self, revision):
        """Remove only the reviewed finished records; never touch recovery or programs."""
        with self.lock:
            if revision != self.clear_review()['revision']:
                raise HistoryChanged('Firing history changed. Review the records again before clearing.')
            identities = [r['id'] for r in self.records.values()
                          if r['simulate'] == self.config.simulate and r['status'] not in ACTIVE]
            # Validate every target before changing anything. Never follow a record symlink.
            root = self.root.resolve()
            for identity in identities:
                path = self.root / identity
                if (not re.fullmatch(r'\d+-[a-f0-9]{10}', identity) or path.is_symlink()
                        or path.resolve().parent != root):
                    raise ValueError('A firing record has an invalid storage path.')
            removed = []
            trash = Path(tempfile.mkdtemp(prefix='.clear-', dir=self.root))
            try:
                for identity in identities:
                    path = self.root / identity
                    if path.exists():
                        # Nested here, a record can no longer be discovered at startup.
                        # An interruption cannot resurrect a successfully removed record.
                        os.replace(path, trash / identity)
                    del self.records[identity]
                    removed.append(identity)
                    if self.current_id == identity:
                        self.current_id = None
                        self.current_points = []
            finally:
                for directory in (self.root, trash):
                    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                atomic_json(self.root / 'averages.json', self.overview())
            shutil.rmtree(trash)
            return removed

    def detail(self, identity):
        with self.lock:
            if identity not in self.records or self.records[identity]['simulate'] != self.config.simulate:
                raise KeyError(identity)
            meta = dict(self.records[identity])
            points = self.read_points(identity)
            meta['stats'] = summarize(points, meta)
            return dict(record=meta, samples=points)


def install_api(app, archive):
    import bottle
    import csv
    import io
    from urllib.parse import urlsplit
    token = secrets.token_urlsafe(32)

    def document():
        with archive.lock:
            return dict(archive.overview(), clear=dict(archive.clear_review(), token=token))

    @app.get('/api/firings')
    def index():
        bottle.response.set_header('Cache-Control', 'no-store')
        return document()

    @app.post('/api/firings/clear')
    def clear():
        bottle.response.set_header('Cache-Control', 'no-store')
        if bottle.request.get_header('X-Kiln-History') != token:
            bottle.abort(403, 'Reload the history page before clearing records.')
        origin = bottle.request.get_header('Origin')
        if origin and urlsplit(origin).netloc != bottle.request.get_header('Host'):
            bottle.abort(403, 'Origin does not match this controller.')
        if bottle.request.content_length > 4096:
            bottle.abort(413, 'Request is too large.')
        body = bottle.request.json
        if not isinstance(body, dict) or body.get('confirm') != 'clear_finished_firings':
            bottle.response.status = 400
            return dict(error='Confirm that you want to clear finished firing records.')
        try:
            removed = archive.clear_finished(body.get('revision'))
        except HistoryChanged as exc:
            bottle.response.status = 409
            return dict(error=str(exc))
        except (OSError, ValueError):
            bottle.response.status = 500
            return dict(error='Some history files could not be cleared. Refresh the page to check the remaining records.')
        return dict(document(), cleared=len(removed), cleared_ids=removed)
    @app.get('/api/firings/<identity>')
    def detail(identity):
        try:
            result = archive.detail(identity)
        except KeyError:
            bottle.abort(404, 'Firing not found')
        bottle.response.set_header('Cache-Control', 'no-store')
        if bottle.request.query.get('format') == 'csv':
            out = io.StringIO()
            keys = ['timestamp','elapsed_seconds','program_seconds','temperature_c','target_c','heater_on_seconds','energy_kwh','cost','state','catching_up','sensor_ready']
            writer = csv.writer(out)
            writer.writerow(keys)
            for p in result['samples']:
                writer.writerow([p.get(k, '') for k in keys])
            bottle.response.content_type = 'text/csv; charset=utf-8'
            bottle.response.set_header('Content-Disposition', 'attachment; filename="firing-'+identity+'.csv"')
            return out.getvalue()
        return result
