import datetime
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import config
from lib.oven import Oven, Profile, RealOven


@pytest.fixture
def kiln(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'automatic_restart_state_file', str(tmp_path / 'state.json'))
    monkeypatch.setattr(config, 'seek_start', False)
    monkeypatch.setattr(config, 'kiln_must_catch_up', True)
    monkeypatch.setattr(config, 'pid_control_window', 3)
    monkeypatch.setattr(config, 'catch_up_tolerance', 0)
    monkeypatch.setattr(config, 'thermocouple_offset', 0)
    sensor = SimpleNamespace(temperature=Mock(return_value=20), ready=Mock(return_value=True),
                             status=SimpleNamespace(over_error_limit=Mock(return_value=False)))
    oven = Oven()
    oven.board = SimpleNamespace(temp_sensor=sensor)
    oven.run_profile(Profile(json.dumps({
        'name': 'ramp-hold-cool',
        'data': [[0, 20], [600, 120], [900, 120], [1500, 20]],
    })))
    return oven


@pytest.fixture
def clock(monkeypatch):
    class ClockDateTime(datetime.datetime):
        current = datetime.datetime(2026, 10, 5, 12)

        @classmethod
        def now(cls, tz=None):
            return cls.current if tz is None else cls.current.astimezone(tz)

    monkeypatch.setattr('lib.oven.datetime.datetime', ClockDateTime)
    return ClockDateTime


@pytest.mark.parametrize('runtime,error,wait', [
    (300, -4, True), (300, -3, False), (300, 3, False), (300, 4, False),
    (750, -4, True), (750, -3, False), (750, 3, False), (750, 4, True),
    (1200, -4, False), (1200, -3, False), (1200, 3, False), (1200, 4, True),
    # At a boundary the new segment determines whether temperature is behind.
    (600, 4, True), (900, -4, False), (900, 4, True),
])
def test_catchup_waits_only_when_behind_ramp_or_outside_hold(kiln, monkeypatch, runtime, error, wait):
    kiln.runtime = runtime
    kiln.update_target_temp()
    kiln.board.temp_sensor.temperature.return_value = kiln.target + error
    kiln.catching_up = True  # A prior wait must clear as soon as it is unnecessary.
    original_start = kiln.start_time
    shifted_start = original_start + datetime.timedelta(seconds=30)
    shift = Mock(return_value=shifted_start)
    monkeypatch.setattr(kiln, 'get_start_time', shift)

    kiln.kiln_must_catch_up()

    assert kiln.catching_up is wait
    assert kiln.start_time == (shifted_start if wait else original_start)
    assert shift.call_count == int(wait)
    assert kiln.runtime == runtime


@pytest.mark.parametrize('runtime,error,wait', [
    (300, -4, True), (300, -3, False), (300, 4, False),
    (750, -4, True), (750, -3, False), (750, 3, False), (750, 4, True),
    (1200, -4, False), (1200, 3, False), (1200, 4, True),
])
def test_explicit_catchup_tolerance_preserves_waits_with_wider_pid_window(
        kiln, monkeypatch, runtime, error, wait):
    monkeypatch.setattr(config, 'pid_control_window', 20)
    monkeypatch.setattr(config, 'catch_up_tolerance', 3)
    kiln.runtime = runtime
    kiln.update_target_temp()
    kiln.board.temp_sensor.temperature.return_value = kiln.target + error

    kiln.kiln_must_catch_up()

    assert kiln.catching_up is wait


@pytest.mark.parametrize('configured', [False, True])
def test_legacy_or_zero_catchup_tolerance_follows_pid_window(kiln, monkeypatch, configured):
    if not configured:
        monkeypatch.delattr(config, 'catch_up_tolerance')
    kiln.runtime = 750
    kiln.update_target_temp()
    kiln.board.temp_sensor.temperature.return_value = kiln.target - 4

    monkeypatch.setattr(config, 'pid_control_window', 5)
    kiln.kiln_must_catch_up()
    assert not kiln.catching_up
    monkeypatch.setattr(config, 'pid_control_window', 3)
    kiln.kiln_must_catch_up()
    assert kiln.catching_up


def test_catchup_tolerance_does_not_change_pid_output_window(kiln, monkeypatch):
    monkeypatch.setattr(config, 'pid_control_window', 20)
    monkeypatch.setattr(config, 'catch_up_tolerance', 3)
    # A 4-degree deficit pauses the program, but stays within proportional
    # control instead of forcing a full 30-second heating pulse.
    kiln.runtime = 300
    kiln.update_target_temp()
    kiln.board.temp_sensor.temperature.return_value = kiln.target - 4
    kiln.pid.kp = 2
    kiln.pid.kd = 0
    kiln.kiln_must_catch_up()
    output = kiln.pid.compute(kiln.target, kiln.target - 4,
                              kiln.pid.lastNow + datetime.timedelta(seconds=30))

    assert kiln.catching_up
    assert 0 < output < 1


def test_heating_overshoot_advances_without_requesting_heat(kiln):
    kiln.profile = Profile(json.dumps({
        'name': 'recorded-overshoot', 'data': [[0, 600], [600, 724], [1200, 800]],
    }))
    kiln.runtime = 600
    kiln.update_target_temp()
    kiln.board.temp_sensor.temperature.return_value = 733

    kiln.kiln_must_catch_up()

    assert not kiln.catching_up
    output = kiln.pid.compute(kiln.target, 733, kiln.pid.lastNow + datetime.timedelta(seconds=30))
    assert output == 0


@pytest.mark.parametrize('temperatures,error,wait', [
    ([20, 120, 20], 4, True),  # Heating to cooling: wait for excess heat.
    ([120, 20, 20], -4, True), ([120, 20, 20], 4, True),  # Cooling to hold.
    ([120, 20, 120], -4, True), ([120, 20, 120], 4, False),  # Cooling to heating.
])
def test_direction_changes_at_exact_program_point(kiln, temperatures, error, wait):
    kiln.profile = Profile(json.dumps({
        'name': 'direction-change',
        'data': [[index * 600, temp] for index, temp in enumerate(temperatures)],
    }))
    kiln.runtime = 600
    kiln.update_target_temp()
    kiln.board.temp_sensor.temperature.return_value = kiln.target + error

    kiln.kiln_must_catch_up()

    assert kiln.catching_up is wait


def test_disabled_catchup_clears_previous_wait(kiln, monkeypatch):
    monkeypatch.setattr(config, 'kiln_must_catch_up', False)
    kiln.catching_up = True
    original_start = kiln.start_time

    kiln.kiln_must_catch_up()

    assert not kiln.catching_up
    assert kiln.start_time == original_start


@pytest.mark.parametrize('runtime', [1500, 1501])
def test_completed_segment_cannot_freeze_schedule(kiln, monkeypatch, runtime):
    kiln.runtime = runtime
    kiln.update_target_temp()
    kiln.catching_up = True
    original_start = kiln.start_time

    kiln.kiln_must_catch_up()

    assert not kiln.catching_up
    assert kiln.start_time == original_start
    if runtime > kiln.totaltime:
        abort = Mock()
        monkeypatch.setattr(kiln, 'abort_run', abort)
        kiln.reset_if_schedule_ended()
        abort.assert_called_once_with('completed')


@pytest.mark.parametrize('segment', [None, (None, None), ([60, 20], [60, 30])])
def test_missing_or_invalid_segment_does_not_freeze(kiln, segment):
    kiln.profile = None if segment is None else SimpleNamespace(get_surrounding_points=lambda _: segment)
    kiln.catching_up = True

    kiln.kiln_must_catch_up()

    assert not kiln.catching_up


def test_warm_start_preserves_seek_without_needing_initial_catchup(kiln, monkeypatch):
    monkeypatch.setattr(config, 'seek_start', True)
    kiln.state = 'IDLE'
    kiln.board.temp_sensor.temperature.return_value = 70
    profile = Profile(json.dumps({'name': 'warm-start', 'data': [[0, 20], [600, 120]]}))

    kiln.run_profile(profile)

    assert kiln.runtime == 300
    assert kiln.target == 70
    kiln.kiln_must_catch_up()
    assert not kiln.catching_up
    kiln.update_runtime()
    assert kiln.runtime == pytest.approx(300, abs=1)


@pytest.mark.parametrize('runtime,temperature,expected_runtime,expected_target', [
    (300, 79, 330, 75),  # Heating ahead: the rising target catches up.
    (300, 61, 300, 70),  # Heating behind: both program clock and target wait.
    (750, 129, 750, 120), (750, 111, 750, 120),  # Holds wait on both sides.
    (750, 120, 780, 120),  # A hold counts time while within its window.
    (1200, 79, 1200, 70), (1200, 61, 1230, 65),  # Cooling behind/ahead.
])
def test_real_program_clock_after_control_cycle(
        kiln, clock, runtime, temperature, expected_runtime, expected_target):
    kiln.run_profile(kiln.profile, startat=runtime / 60, allow_seek=False)
    kiln.board.temp_sensor.temperature.return_value = temperature
    clock.current += datetime.timedelta(seconds=30)

    # Match the production loop after the preceding 30-second control cycle.
    kiln.kiln_must_catch_up()
    kiln.update_runtime()
    kiln.update_target_temp()

    assert kiln.runtime == expected_runtime
    assert kiln.target == expected_target
    assert kiln.catching_up is (expected_runtime == runtime)


def test_restored_program_position_sets_clock_without_warm_seek(kiln, clock, monkeypatch):
    monkeypatch.setattr(config, 'seek_start', True)
    kiln.state = 'IDLE'
    kiln.board.temp_sensor.temperature.return_value = 100
    saved_runtime = 195

    # Automatic recovery supplies the saved position and explicitly disables seek.
    kiln.run_profile(kiln.profile, startat=saved_runtime / 60, allow_seek=False)

    assert kiln.runtime == saved_runtime
    assert kiln.target == 52.5
    assert kiln.start_time == clock.current - datetime.timedelta(seconds=saved_runtime)
    clock.current += datetime.timedelta(seconds=30)
    kiln.kiln_must_catch_up()
    kiln.update_runtime()
    kiln.update_target_temp()
    assert kiln.runtime == saved_runtime + 30
    assert kiln.target == 57.5


def test_allowing_heating_overshoot_keeps_sensor_shutdown(kiln, monkeypatch):
    kiln.runtime = 300
    kiln.update_target_temp()
    kiln.board.temp_sensor.temperature.return_value = kiln.target + 9
    kiln.kiln_must_catch_up()
    assert not kiln.catching_up
    kiln.board.temp_sensor.ready.return_value = False
    kiln.output = Mock()
    abort = Mock()
    monkeypatch.setattr(kiln, 'abort_run', abort)
    monkeypatch.setattr('lib.oven.time.sleep', lambda _: None)

    RealOven.heat_then_cool(kiln)

    abort.assert_called_once_with('sensor_fault')
    kiln.output.heat.assert_not_called()
    kiln.output.cool.assert_called_once_with(0)


def test_allowing_heating_overshoot_keeps_overtemperature_shutdown(kiln, monkeypatch):
    monkeypatch.setattr(config, 'emergency_shutoff_temp', 75)
    monkeypatch.setattr(config, 'ignore_temp_too_high', False)
    kiln.runtime = 300
    kiln.update_target_temp()
    kiln.board.temp_sensor.temperature.return_value = 80
    kiln.kiln_must_catch_up()
    assert not kiln.catching_up
    abort = Mock()
    monkeypatch.setattr(kiln, 'abort_run', abort)

    kiln.reset_if_emergency()

    abort.assert_called_once_with('over_temperature')
