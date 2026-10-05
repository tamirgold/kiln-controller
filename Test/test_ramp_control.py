"""Pure tests for rate feedback; no hardware or running controller required."""
import math

import pytest

from lib.ramp_control import RampController


def observe(controller, now, *, actual_rate=30.0, requested_rate=60.0,
            start=600.0, target=None, **overrides):
    temperature = start + actual_rate * now / 3600
    arguments = dict(now=now, temperature=temperature,
                     # Isolate rate feedback from the separate temperature PID.
                     target=temperature if target is None else target,
                     segment=(0, start, 3600, start + requested_rate),
                     pid_output=.5)
    arguments.update(overrides)
    output = controller.update(**arguments)
    return output, controller.snapshot()


def drive(controller, *, duration=900, step=30, **arguments):
    return [(now, *observe(controller, now, **arguments))
            for now in range(0, duration + 1, step)]


def with_trim(direction=1):
    controller = RampController()
    drive(controller, duration=600, actual_rate=0 if direction > 0 else 120)
    assert controller.snapshot()['trim_percent'] == pytest.approx(10 * direction)
    return controller


@pytest.mark.parametrize('requested,actual,direction,phase', [
    (60, 30, 1, 'heating'),
    (60, 90, -1, 'heating'),
    (-60, -30, -1, 'cooling'),
    (-60, -90, 1, 'cooling'),
])
def test_signed_rate_error_corrects_heating_and_cooling(requested, actual, direction, phase):
    controller = RampController()
    _, output, report = drive(controller, actual_rate=actual, requested_rate=requested)[-1]

    assert report['phase'] == phase
    assert report['requested_rate'] == pytest.approx(requested)
    assert report['measured_rate'] == pytest.approx(actual)
    assert report['rate_error'] == pytest.approx(requested - actual)
    assert (output - .5) * direction > 0
    assert report['applied_trim_percent'] * direction > 0
    assert report['correction_count'] > 0


def test_matching_ramp_does_not_change_power():
    controller = RampController()
    reports = drive(controller, actual_rate=60, duration=1800)

    assert all(output == .5 for _, output, _ in reports)
    assert reports[-1][2]['status'] == 'tracking'
    assert reports[-1][2]['correction_count'] == 0


def test_requires_five_minutes_and_two_confirmed_checks_before_correction():
    controller = RampController()
    reports = drive(controller, duration=360, actual_rate=0)

    for now, output, report in reports:
        if now < 300:
            assert report['measured_rate'] is None
            assert report['status'] == 'collecting'
        if now < 360:
            assert output == .5
            assert report['correction_count'] == 0
    assert reports[-1][1] > .5
    assert reports[-1][2]['correction_count'] == 1


def test_checks_once_per_minute_and_duplicate_observation_cannot_advance_learning():
    controller = RampController()
    drive(controller, duration=360, actual_rate=0)
    before = controller.snapshot()

    for _ in range(20):
        _, repeated = observe(controller, 360, actual_rate=0)
        assert repeated == before
    _, halfway = observe(controller, 390, actual_rate=0)
    assert halfway['correction_count'] == before['correction_count']
    assert halfway['trim_percent'] == before['trim_percent']
    assert halfway['next_check_seconds'] == pytest.approx(30)
    _, next_check = observe(controller, 420, actual_rate=0)
    assert next_check['correction_count'] == before['correction_count'] + 1
    assert next_check['next_check_seconds'] == pytest.approx(60)


def test_reversed_rate_error_requires_fresh_confirmations():
    controller = with_trim()
    checked = []
    for now in range(630, 1801, 30):
        temperature = 600 + (now - 600) / 30
        controller.update(now=now, temperature=temperature, target=temperature,
                          segment=(0, 600, 3600, 660), pid_output=.5)
        if now % 60 == 0:
            checked.append(controller.snapshot())

    first = next(index for index, report in enumerate(checked)
                 if report['rate_error'] < -report['rate_deadband'])
    assert first > 0
    assert checked[first]['trim_percent'] == checked[first - 1]['trim_percent']
    assert checked[first + 1]['trim_percent'] < checked[first]['trim_percent']


@pytest.mark.parametrize('actual,direction', [(0, 1), (120, -1)])
def test_learning_slew_and_total_correction_remain_bounded(actual, direction):
    controller = RampController()
    reports = drive(controller, actual_rate=actual, duration=1800)
    changed = []
    previous_trim = 0
    for now, output, report in reports:
        trim = report['trim_percent']
        assert -10 <= trim <= 10
        assert .4 - 1e-12 <= output <= .6 + 1e-12
        if abs(trim - previous_trim) > 1e-9:
            assert abs(trim - previous_trim) <= 2 + 1e-9
            changed.append(now)
        previous_trim = trim

    assert reports[-1][2]['trim_percent'] == pytest.approx(10 * direction)
    assert all(second - first >= 60 for first, second in zip(changed, changed[1:]))


def test_trim_limit_remains_visible_between_periodic_checks():
    controller = RampController()
    reports = drive(controller, actual_rate=0, duration=750)
    # The requested rate still exceeds the measured rate once the allowed
    # correction is exhausted, including the intervening 30-second samples.
    for now, _, report in reports:
        if now >= 660:
            assert report['status'] in ('power_limit', 'correction_limit')


@pytest.mark.parametrize('requested,actual,base', [(60, 30, 1), (-60, -30, 0)])
def test_heater_or_natural_cooling_limit_is_persistent_without_windup(requested, actual, base):
    controller = RampController()
    reports = drive(controller, requested_rate=requested, actual_rate=actual,
                    pid_output=base, duration=900)

    for now, output, report in reports:
        assert output == base
        assert report['trim_percent'] == 0
        if now >= 300:
            assert report['status'] == 'power_limit'


@pytest.mark.parametrize('base', [0.0, 1.0])
@pytest.mark.parametrize('direction', [-1, 1])
def test_learned_trim_cannot_override_hard_pid_output(base, direction):
    controller = with_trim(direction)
    output, report = observe(controller, 630, actual_rate=0 if direction > 0 else 120,
                             pid_output=base)

    assert output == base
    assert report['applied_trim_percent'] == 0
    assert report['status'] in ('temperature_priority', 'power_limit')


def test_low_temperature_output_cap_wins_over_positive_trim():
    controller = with_trim()
    output, report = observe(controller, 630, actual_rate=0, pid_output=.39, max_output=.4)
    assert output == pytest.approx(.4)
    assert report['applied_trim_percent'] == pytest.approx(1)

    output, report = observe(controller, 660, actual_rate=0, pid_output=1, max_output=.4)
    assert output == pytest.approx(.4)
    assert report['applied_trim_percent'] == 0
    assert report['status'] == 'power_limit'


@pytest.mark.parametrize('direction', [-1, 1])
def test_temperature_priority_blocks_trim_that_would_increase_temperature_error(direction):
    controller = with_trim(direction)
    actual = 0 if direction > 0 else 120
    current = 600 + actual * 630 / 3600
    output, report = observe(controller, 630, actual_rate=actual,
                             target=current - direction * 3)

    assert output == .5
    assert report['applied_trim_percent'] == 0
    assert report['status'] == 'temperature_priority'


def test_pid_safety_reading_has_priority_over_cycle_mean():
    controller = with_trim()
    output, report = observe(controller, 630, actual_rate=0, control_temperature=604)

    assert report['measured_rate'] == pytest.approx(0)
    assert report['status'] == 'temperature_priority'
    assert output == .5


def test_control_window_guard_is_independent_of_catchup_tolerance():
    controller = with_trim()
    output, report = observe(controller, 630, actual_rate=0, target=612,
                             tolerance=20, control_window=10)

    assert output == .5
    assert report['applied_trim_percent'] == 0
    assert report['status'] == 'temperature_priority'


@pytest.mark.parametrize('override,phase,status', [
    ({'segment': (0, 600, 3600, 600)}, 'hold', 'hold'),
    ({'state': 'PAUSED'}, 'paused', 'paused'),
    ({'enabled': False}, 'heating', 'disabled'),
])
def test_hold_pause_or_disable_removes_learned_correction(override, phase, status):
    controller = with_trim()
    output, report = observe(controller, 630, actual_rate=0, **override)

    assert output == .5
    assert report['phase'] == phase
    assert report['status'] == status
    assert report['trim_percent'] == 0
    assert report['applied_trim_percent'] == 0
    assert report['correction_count'] == 0


@pytest.mark.parametrize('override', [{'state': 'PAUSED'}, {'enabled': False}])
def test_resume_or_reenable_recollects_samples(override):
    controller = with_trim()
    observe(controller, 630, actual_rate=0, **override)
    for now in range(660, 1201, 30):
        observe(controller, now, actual_rate=0, **override)
    output, report = observe(controller, 1230, actual_rate=0)

    assert output == .5
    assert report['status'] == 'collecting'
    assert report['sample_count'] == 1
    assert report['measured_rate'] is None


def test_current_segment_change_discards_previous_ramp_and_correction():
    controller = with_trim()
    output, report = observe(controller, 630, requested_rate=-60, actual_rate=-30)

    assert output == .5
    assert report['phase'] == 'cooling'
    assert report['requested_rate'] == pytest.approx(-60)
    assert report['measured_rate'] is None
    assert report['sample_count'] == 1
    assert report['trim_percent'] == 0


@pytest.mark.parametrize('next_time', [599, 691])
def test_reverse_monotonic_clock_or_sampling_gap_restarts_measurement(next_time):
    controller = with_trim()
    output, report = observe(controller, next_time, actual_rate=0)

    assert output == .5
    assert report['status'] == 'collecting'
    assert report['sample_count'] == 1
    assert report['measured_rate'] is None
    assert report['trim_percent'] == 0


def test_a_valid_90_second_gap_keeps_measurement():
    controller = with_trim()
    _, report = observe(controller, 690, actual_rate=0)
    assert report['measured_rate'] == pytest.approx(0)
    assert report['sample_count'] > 1


def test_measurement_uses_elapsed_observations_while_program_target_is_frozen():
    controller = RampController()
    reports = drive(controller, duration=600, actual_rate=30, target=605)

    assert reports[-1][2]['requested_rate'] == pytest.approx(60)
    assert reports[-1][2]['measured_rate'] == pytest.approx(30)
    assert reports[-1][1] > .5


def test_large_monotonic_origin_does_not_change_rate_or_correction():
    ordinary, shifted = RampController(), RampController()
    for now in range(0, 901, 30):
        temperature = 600 + now / 120
        first = ordinary.update(now=now, temperature=temperature, target=temperature,
                                segment=(0, 600, 3600, 660), pid_output=.5)
        second = shifted.update(now=1_000_000_000 + now, temperature=temperature, target=temperature,
                                segment=(0, 600, 3600, 660), pid_output=.5)
        assert second == pytest.approx(first)
    assert shifted.snapshot()['measured_rate'] == pytest.approx(30)


def test_fahrenheit_and_celsius_produce_equivalent_correction():
    celsius, fahrenheit = RampController(), RampController()
    for now in range(0, 901, 30):
        temperature = 600 + now / 120
        out_c = celsius.update(now=now, temperature=temperature, target=temperature,
                               segment=(0, 600, 3600, 660), pid_output=.5)
        out_f = fahrenheit.update(now=now, temperature=temperature * 1.8 + 32,
                                  target=temperature * 1.8 + 32,
                                  segment=(0, 600 * 1.8 + 32, 3600, 660 * 1.8 + 32),
                                  pid_output=.5, tolerance=5, control_window=18, scale=1.8)
        assert out_f == pytest.approx(out_c)

    report_c, report_f = celsius.snapshot(), fahrenheit.snapshot()
    for field in ('requested_rate', 'measured_rate', 'rate_error', 'rate_deadband'):
        assert report_f[field] == pytest.approx(report_c[field] * 1.8)


@pytest.mark.parametrize('override', [
    {'sensor_ready': False}, {'temperature': float('nan')}, {'temperature': float('inf')},
    {'control_temperature': float('nan')}, {'target': float('inf')},
    {'now': float('nan')}, {'tolerance': 0}, {'control_window': 0}, {'scale': 0},
])
def test_invalid_sensor_or_control_input_fails_closed_and_clears_history(override):
    controller = with_trim()
    arguments = dict(now=630, temperature=600, target=600,
                     segment=(0, 600, 3600, 660), pid_output=.5)
    arguments.update(override)
    output = controller.update(**arguments)
    report = controller.snapshot()

    assert output == 0
    assert report['status'] == 'sensor_fault'
    assert report['sample_count'] == 0
    assert report['trim_percent'] == 0
    assert report['measured_rate'] is None


@pytest.mark.parametrize('override', [{'pid_output': float('nan')}, {'max_output': float('nan')}])
def test_nonfinite_actuator_request_fails_closed(override):
    controller = with_trim()
    output, report = observe(controller, 630, actual_rate=0, **override)
    assert output == 0
    assert report['applied_trim_percent'] == 0


def test_noise_dependent_deadband_rejects_relay_ripple():
    controller = RampController()
    reports = []
    for now in range(0, 1801, 30):
        temperature = 600 + now / 60 + 6 * math.sin(2 * math.pi * now / 120)
        output = controller.update(now=now, temperature=temperature, target=temperature,
                                   segment=(0, 600, 3600, 660), pid_output=.5)
        reports.append((output, controller.snapshot()))

    assert all(output == .5 for output, _ in reports)
    assert reports[-1][1]['rate_deadband'] > 60 * .08
    assert reports[-1][1]['correction_count'] == 0


def test_measurement_keeps_a_recent_window_instead_of_all_firing_history():
    controller = RampController()
    for now in range(0, 2401, 30):
        temperature = 600 + min(now, 1200) / 60 + max(0, now - 1200) / 120
        controller.update(now=now, temperature=temperature, target=temperature,
                          segment=(0, 600, 3600, 660), pid_output=.5)

    report = controller.snapshot()
    assert report['measured_rate'] == pytest.approx(30)
    assert report['window_seconds'] <= 630
    assert report['sample_count'] <= 22
    assert report['trim_percent'] > 0


def test_snapshot_is_a_copy_and_reset_clears_learned_state():
    controller = with_trim()
    report = controller.snapshot()
    report['trim_percent'] = 999
    assert controller.snapshot()['trim_percent'] == pytest.approx(10)

    controller.reset()
    assert controller.snapshot()['status'] == 'idle'
    assert controller.snapshot()['trim_percent'] == 0
    assert controller.snapshot()['correction_count'] == 0
    assert controller.snapshot()['measured_rate'] is None
