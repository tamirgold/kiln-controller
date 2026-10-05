"""Slow, bounded ramp-rate feedback around the temperature PID.

The schedule and PID gains are never changed. Inputs use monotonic elapsed
seconds and the configured temperature unit; output is heater duty (0..1).
"""
import math
import statistics


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def clamp(value, low, high):
    return min(high, max(low, value))


class RampController:
    WINDOW = 600.0
    MINIMUM_WINDOW = 300.0
    INTERVAL = 60.0
    MAX_GAP = 90.0
    MAX_TRIM = .10
    MAX_STEP = .02

    def __init__(self):
        self.reset()

    def reset(self):
        self.samples = []
        self.key = None
        self.trim = 0.0
        self.last_check = None
        self.direction = 0
        self.confirmations = 0
        self.corrections = 0
        self.report = dict(enabled=False, status='idle', phase='idle',
                           requested_rate=None, measured_rate=None, rate_error=None,
                           rate_deadband=None, trim_percent=0.0, applied_trim_percent=0.0,
                           pid_output_percent=0.0, output_percent=0.0, sample_count=0,
                           window_seconds=0.0, minimum_window_seconds=self.MINIMUM_WINDOW,
                           measurement_window_seconds=self.WINDOW,
                           check_interval_seconds=self.INTERVAL, next_check_seconds=None,
                           correction_count=0, max_trim_percent=self.MAX_TRIM * 100)

    def snapshot(self):
        return dict(self.report)

    def trend(self):
        if len(self.samples) < 6 or self.samples[-1][0] - self.samples[0][0] < self.MINIMUM_WINDOW:
            return None, None
        origin = self.samples[0][0]
        times = [p[0] - origin for p in self.samples]
        values = [p[1] for p in self.samples]
        mean_t, mean_y = statistics.mean(times), statistics.mean(values)
        variance = sum((t - mean_t) ** 2 for t in times)
        if variance <= 0:
            return None, None
        slope = sum((t - mean_t) * (y - mean_y) for t, y in zip(times, values)) / variance
        residual = sum((y - mean_y - slope * (t - mean_t)) ** 2 for t, y in zip(times, values))
        uncertainty = math.sqrt(residual / (len(times) - 2) / variance) * 3600
        return slope * 3600, uncertainty

    def update(self, *, now, temperature, target, segment, pid_output,
               enabled=True, state='RUNNING', sensor_ready=True, tolerance=2.7777777778,
               control_window=10.0, max_output=1.0, scale=1.0, control_temperature=None):
        """Observe one complete control cycle and return bounded final duty.

        `temperature` is the cycle mean; `control_temperature` is the existing
        PID/safety reading. Holds and pauses retain ordinary temperature PID.
        Cooling uses the same signed rate feedback, but can only reduce heat
        to zero or add heat to slow an excessively fast temperature fall.
        """
        maximum = clamp(max_output, 0, 1) if finite(max_output) else 0
        base = clamp(pid_output, 0, maximum) if finite(pid_output) else 0
        current = temperature if control_temperature is None else control_temperature
        valid = (sensor_ready and all(finite(v) for v in (now, temperature, current, target, tolerance, control_window, scale, pid_output, max_output))
                 and tolerance > 0 and control_window > 0 and scale > 0)
        valid_segment = (isinstance(segment, (tuple, list)) and len(segment) == 4
                         and all(finite(v) for v in segment) and segment[2] > segment[0])
        if not valid or not valid_segment or state not in ('RUNNING', 'PAUSED'):
            self.reset()
            output = 0.0 if not valid else base
            self.report.update(enabled=bool(enabled), status='sensor_fault' if not valid else 'idle',
                               pid_output_percent=base * 100, output_percent=output * 100)
            return output

        requested = (segment[3] - segment[1]) / (segment[2] - segment[0]) * 3600
        phase = 'paused' if state == 'PAUSED' else 'hold' if requested == 0 else 'heating' if requested > 0 else 'cooling'
        key = (tuple(segment), state, bool(enabled), scale)
        if (key != self.key or self.samples and
                (now < self.samples[-1][0] or now - self.samples[-1][0] > self.MAX_GAP)):
            self.reset()
            self.key = key
        # Polling must not change the sample weighting or correction cadence.
        if not self.samples or now > self.samples[-1][0]:
            self.samples.append((now, temperature))
        while len(self.samples) > 1 and self.samples[1][0] <= now - self.WINDOW:
            self.samples.pop(0)
        measured, uncertainty = self.trend()
        desired = 0.0 if phase in ('hold', 'paused') else requested
        error = desired - measured if measured is not None else None
        deadband = max(3 * scale, abs(desired) * .08, uncertainty * 1.5) if uncertainty is not None else None
        observed = self.samples[-1][0] - self.samples[0][0]
        status = 'disabled' if not enabled else phase if phase in ('hold', 'paused') else 'collecting' if measured is None else 'tracking'

        def permitted(direction, learning=False):
            # Neither the rate observer nor an accumulated trim may override
            # the PID's full heating/cooling decision or a temperature wait.
            if direction > 0 and current > target + tolerance:
                return 'temperature_priority'
            if direction < 0 and current < target - tolerance:
                return 'temperature_priority'
            if (direction > 0 and base >= maximum - 1e-9) or (direction < 0 and base <= 1e-9):
                return 'power_limit'
            if abs(target - current) > control_window:
                return 'temperature_priority'
            if learning and ((direction > 0 and base + self.trim >= maximum - 1e-9)
                             or (direction < 0 and base + self.trim <= 1e-9)):
                return 'power_limit'
            if base <= 1e-9 or base >= maximum - 1e-9:
                return 'temperature_priority'
            return None

        if not enabled or phase in ('hold', 'paused'):
            self.trim = 0.0
            self.direction = self.confirmations = 0
            self.last_check = None
        elif measured is not None and (self.last_check is None or now - self.last_check >= self.INTERVAL):
            self.last_check = now
            direction = 1 if error > deadband else -1 if error < -deadband else 0
            self.confirmations = self.confirmations + 1 if direction and direction == self.direction else int(bool(direction))
            self.direction = direction
            blocked = permitted(direction, learning=True) if direction else None
            if blocked:
                status = blocked
                # No integral windup against unavailable power or temperature
                # priority. Unwind an old correction in the blocked direction.
                if self.trim * direction > 0:
                    self.trim -= math.copysign(min(abs(self.trim), self.MAX_STEP), self.trim)
            elif direction and self.confirmations >= 2:
                amount = self.MAX_STEP * clamp(error / max(abs(desired), 30 * scale), -1, 1)
                proposed = clamp(self.trim + amount, -self.MAX_TRIM, self.MAX_TRIM)
                if abs(proposed - self.trim) > 1e-9:
                    self.corrections += 1
                    self.trim = proposed
                    status = 'correcting'
                else:
                    status = 'correction_limit'

        applied = self.trim if enabled and phase in ('heating', 'cooling') else 0.0
        if applied:
            blocked = permitted(1 if applied > 0 else -1)
            if blocked:
                applied = 0.0
                status = blocked
        corrected = clamp(base + applied, 0, maximum)
        # Outside this update instant, expose a persistent applied correction.
        if status == 'tracking' and abs(corrected - base) > 1e-9:
            status = 'correcting'
        if enabled and measured is not None and phase in ('heating', 'cooling'):
            direction = 1 if error > deadband else -1 if error < -deadband else 0
            blocked = permitted(direction, learning=True) if direction else None
            if blocked:
                status = blocked
            elif direction and self.trim * direction >= self.MAX_TRIM - 1e-9:
                status = 'correction_limit'
            elif direction and (self.confirmations < 2 or direction != self.direction):
                status = 'confirming'
        remaining = max(0, self.MINIMUM_WINDOW - observed) if measured is None else max(0, self.INTERVAL - (now - self.last_check)) if self.last_check is not None else None
        self.report.update(enabled=bool(enabled), status=status, phase=phase,
                           requested_rate=desired, measured_rate=measured, rate_error=error,
                           rate_deadband=deadband, trim_percent=self.trim * 100,
                           applied_trim_percent=(corrected - base) * 100,
                           pid_output_percent=base * 100, output_percent=corrected * 100,
                           sample_count=len(self.samples), window_seconds=observed,
                           next_check_seconds=remaining, correction_count=self.corrections)
        return corrected
