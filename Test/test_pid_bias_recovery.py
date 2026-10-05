"""Recover only a recent, healthy PID heat bias; never a saved heat command."""
import copy
import datetime
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import config
from lib.oven import Oven, Profile, RealOven


@pytest.fixture
def recovery_case(tmp_path, monkeypatch):
    for key, value in {
        'automatic_restart_state_file': str(tmp_path / 'state.json'),
        'automatic_restarts': True, 'automatic_restart_window': 25,
        'require_synced_clock_for_restart': False, 'simulate': False,
        'seek_start': False, 'temp_scale': 'c', 'sensor_time_wait': 30,
        'pid_control_window': 10, 'catch_up_tolerance': 2.7777777778,
        'pid_kp': 4, 'pid_ki': 90, 'pid_kd': 30,
        'automatic_ramp_control': True, 'thermocouple_offset': 0,
        'throttle_below_temp': 150, 'throttle_percent': 100,
        'emergency_shutoff_temp': 1240, 'ignore_temp_too_high': False,
        'ignore_tc_too_many_errors': False,
    }.items():
        monkeypatch.setattr(config, key, value)
    clock = SimpleNamespace(now=time.time())

    class ClockedDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromtimestamp(clock.now, tz)

    monkeypatch.setattr('lib.oven.time.time', lambda: clock.now)
    monkeypatch.setattr('lib.oven.datetime.datetime', ClockedDateTime)
    sensor = SimpleNamespace(
        temperature=Mock(return_value=1018.0),
        cycle_temperature=Mock(return_value=1018.0),
        ready=Mock(return_value=True),
        status=SimpleNamespace(over_error_limit=Mock(return_value=False)),
    )
    kiln = Oven()
    kiln.board = SimpleNamespace(temp_sensor=sensor)
    profile_data = {'name': 'high-temperature recovery',
                    'data': [[0, 990], [3600, 1050], [4200, 1050], [7800, 990]]}
    kiln.run_profile(Profile(json.dumps(profile_data)), startat=30, allow_seek=False)
    saved = dict(
        saved_at=clock.now - 30, timestamp=clock.now - 30,
        temp_scale='c', simulate=False, sensor_ready=True, state='RUNNING',
        profile=profile_data['name'], profile_data=copy.deepcopy(profile_data),
        runtime=1800, cost=2.0, run_started_at=clock.now - 10000,
        temperature=1019.0, target=1020.0,
        pidstats=dict(i=72.0, out=.85, ispoint=1019.0, setpoint=1020.0,
                      err=1.0, time=clock.now - 60,
                      kp=8, ki=44.4444444444, kd=100),
        ramp_control=dict(trim_percent=8.0, correction_count=20),
    )
    return kiln, saved, clock


def persist(saved):
    path = Path(config.automatic_restart_state_file)
    path.write_text(json.dumps(saved))
    # The fixture freezes wall time before writing, so use the same simulated
    # save time for the existing filesystem-age recovery guard.
    os.utime(path, (saved['saved_at'], saved['saved_at']))


def control_memory(kiln):
    return (kiln.pid.iterm, kiln.pid.lastErr, kiln.pid.lastNow,
            copy.deepcopy(kiln.pid.pidstats), kiln.ramp_control.snapshot(),
            list(kiln.ramp_control.samples))


def test_short_recovery_restores_only_bias_with_new_gains(recovery_case):
    kiln, saved, clock = recovery_case
    original = copy.deepcopy(saved)
    target, runtime, profile = kiln.target, kiln.runtime, copy.deepcopy(kiln.profile.data)
    ramp_before = kiln.ramp_control.snapshot()

    assert kiln.restore_pid_bias(saved) is True

    assert kiln.pid.iterm == 72
    assert (kiln.pid.kp, kiln.pid.ki, kiln.pid.kd) == (4, 90, 30)
    assert kiln.pid.lastErr == 2
    assert (datetime.datetime.now() - kiln.pid.lastNow).total_seconds() == pytest.approx(30)
    assert kiln.pid.pidstats == {}
    assert kiln.ramp_control.snapshot() == ramp_before
    assert kiln.ramp_control.samples == []
    assert (kiln.target, kiln.runtime, kiln.profile.data) == (target, runtime, profile)
    assert saved == original


def test_first_computation_has_no_stale_derivative_or_downtime_integral(recovery_case):
    kiln, saved, _ = recovery_case
    saved['saved_at'] -= 30
    saved['pidstats']['time'] -= 30
    saved['pidstats']['err'] = -4
    saved['pidstats']['ispoint'] = 1024
    assert kiln.restore_pid_bias(saved)

    duty = kiln.controlled_heat_duty(datetime.datetime.now(), 0)

    assert kiln.pid.pidstats['timeDelta'] == pytest.approx(30)
    assert kiln.pid.pidstats['d'] == pytest.approx(0)
    expected_integral = 72 + 2 * 30 / 90
    assert kiln.pid.iterm == pytest.approx(expected_integral)
    assert duty == pytest.approx((4 * 2 + expected_integral) / 100)
    assert kiln.pid.pidstats['base_out'] == kiln.pid.pidstats['out']
    assert kiln.ramp_control.trim == 0


@pytest.mark.parametrize('age,accepted', [(0, True), (30, True), (90, True), (90.01, False), (-.01, False)])
def test_bias_recovery_age_is_limited_to_three_cycles(recovery_case, age, accepted):
    kiln, saved, clock = recovery_case
    saved['saved_at'] = clock.now - age
    saved['pidstats']['time'] = saved['saved_at'] - 30
    before = control_memory(kiln)

    assert kiln.restore_pid_bias(saved) is accepted
    if not accepted:
        assert control_memory(kiln) == before


@pytest.mark.parametrize('decision_age,accepted', [(0, True), (60, True), (60.01, False), (-.01, False)])
def test_saved_pid_decision_must_be_recent_when_state_was_saved(recovery_case, decision_age, accepted):
    kiln, saved, _ = recovery_case
    saved['pidstats']['time'] = saved['saved_at'] - decision_age

    assert kiln.restore_pid_bias(saved) is accepted


@pytest.mark.parametrize('field,value', [
    ('i', -1), ('i', 100.01), ('i', True), ('i', None), ('i', '72'),
    ('i', float('nan')), ('i', float('inf')),
    ('out', 0), ('out', -.01), ('out', 1.01), ('out', True),
    ('out', float('nan')), ('out', float('inf')),
    ('ispoint', None), ('ispoint', True), ('ispoint', float('nan')),
    ('setpoint', '1020'), ('setpoint', True), ('setpoint', float('inf')),
    ('err', -10.01), ('err', 10.01), ('err', True), ('err', float('nan')),
    ('time', True), ('time', None), ('time', float('inf')),
])
def test_invalid_or_suspended_pid_decision_is_not_restored(recovery_case, field, value):
    kiln, saved, _ = recovery_case
    saved['pidstats'][field] = value
    before = control_memory(kiln)

    assert kiln.restore_pid_bias(saved) is False
    assert control_memory(kiln) == before


@pytest.mark.parametrize('field,value', [
    ('saved_at', True), ('saved_at', float('nan')), ('saved_at', float('inf')),
    ('state', 'IDLE'), ('state', 'PAUSED'), ('sensor_ready', False), ('sensor_ready', 1),
    ('temp_scale', 'f'), ('simulate', True),
    ('profile_data', {'name': 'different', 'data': [[0, 990], [3600, 1050]]}),
    ('pidstats', None), ('pidstats', {}),
])
def test_ineligible_saved_state_cannot_restore_bias(recovery_case, field, value):
    kiln, saved, _ = recovery_case
    saved[field] = value
    before = control_memory(kiln)

    assert kiln.restore_pid_bias(saved) is False
    assert control_memory(kiln) == before


@pytest.mark.parametrize('document', [None, [], {}, 'invalid'])
def test_missing_or_legacy_bias_metadata_is_optional(recovery_case, document):
    kiln, _, _ = recovery_case
    before = control_memory(kiln)

    assert kiln.restore_pid_bias(document) is False
    assert control_memory(kiln) == before


@pytest.mark.parametrize('failure', ['unready', 'missing_board', 'missing_sensor', 'cold', 'hot',
                                     'changed_reading', 'nan', 'infinite', 'missing_reading',
                                     'target_nan', 'target_infinite', 'emergency'])
def test_fresh_temperature_and_board_guards(recovery_case, monkeypatch, failure):
    kiln, saved, _ = recovery_case
    if failure == 'unready':
        kiln.board.temp_sensor.ready.return_value = False
    elif failure == 'missing_board':
        del kiln.board
    elif failure == 'missing_sensor':
        del kiln.board.temp_sensor
    elif failure == 'cold':
        kiln.board.temp_sensor.temperature.return_value = 1009.9
    elif failure == 'hot':
        kiln.board.temp_sensor.temperature.return_value = 1030.1
    elif failure == 'changed_reading':
        # Both old/new readings individually remain inside the target window,
        # but a large intervening temperature change makes the bias stale.
        saved['pidstats'].update(ispoint=1028, err=-8)
        kiln.board.temp_sensor.temperature.return_value = 1011
    elif failure in ('nan', 'infinite', 'missing_reading'):
        kiln.board.temp_sensor.temperature.return_value = {
            'nan': float('nan'), 'infinite': float('inf'), 'missing_reading': None,
        }[failure]
    elif failure.startswith('target_'):
        kiln.target = float('nan') if failure == 'target_nan' else float('inf')
    else:
        monkeypatch.setattr(config, 'emergency_shutoff_temp', 1018)
    before = control_memory(kiln)

    assert kiln.restore_pid_bias(saved) is False
    assert control_memory(kiln) == before


def test_temperature_offset_is_applied_exactly_once(recovery_case, monkeypatch):
    kiln, saved, _ = recovery_case
    monkeypatch.setattr(config, 'thermocouple_offset', 7)
    kiln.board.temp_sensor.temperature.return_value = 1011

    assert kiln.restore_pid_bias(saved)
    assert kiln.pid.lastErr == 2


def test_simulated_recovery_still_needs_a_temperature_but_not_real_sensor_ready(recovery_case, monkeypatch):
    kiln, saved, _ = recovery_case
    monkeypatch.setattr(config, 'simulate', True)
    saved['simulate'] = True
    kiln.board.temp_sensor.ready.return_value = False

    assert kiln.restore_pid_bias(saved)
    assert kiln.pid.iterm == 72


def test_automatic_restart_restores_bias_only_after_resuming_original_program(recovery_case, monkeypatch):
    kiln, saved, _ = recovery_case
    persist(saved)
    kiln.reset()
    restore = Mock(wraps=kiln.restore_pid_bias)
    monkeypatch.setattr(kiln, 'restore_pid_bias', restore)

    kiln.automatic_restart()

    restore.assert_called_once_with(saved)
    assert kiln.state == 'RUNNING'
    assert kiln.runtime == saved['runtime']
    assert kiln.profile.data == saved['profile_data']['data']
    assert kiln.run_started_at == saved['run_started_at']
    assert kiln.pid.iterm == 72
    assert kiln.ramp_control.trim == 0
    assert kiln.ramp_control.samples == []
    assert json.loads(Path(config.automatic_restart_state_file).read_text()) == saved


@pytest.mark.parametrize('runtime,target,temperature,phase,rate', [
    (3900, 1050, 1048, 'hold', 0),
    (4800, 1040, 1042, 'cooling', -60),
])
def test_recovery_retains_hold_or_cooling_segment_without_old_ramp_trim(
        recovery_case, runtime, target, temperature, phase, rate):
    kiln, saved, _ = recovery_case
    saved.update(runtime=runtime, target=target)
    saved['pidstats'].update(setpoint=target, ispoint=target - 1, err=1)
    kiln.board.temp_sensor.temperature.return_value = temperature
    kiln.board.temp_sensor.cycle_temperature.return_value = temperature
    persist(saved)
    kiln.reset()

    kiln.automatic_restart()
    assert kiln.pid.iterm == 72
    kiln.controlled_heat_duty(datetime.datetime.now(), 0)

    assert kiln.runtime == runtime
    assert kiln.target == target
    report = kiln.ramp_control.snapshot()
    assert report['phase'] == phase
    assert report['requested_rate'] == rate
    assert report['measured_rate'] is None
    assert report['trim_percent'] == report['applied_trim_percent'] == 0


def test_long_outage_can_resume_program_without_restoring_old_heat_bias(recovery_case):
    kiln, saved, clock = recovery_case
    saved['saved_at'] = clock.now - 120
    saved['pidstats']['time'] = saved['saved_at'] - 30
    persist(saved)
    kiln.reset()

    kiln.automatic_restart()

    assert kiln.state == 'RUNNING'
    assert kiln.runtime == saved['runtime']
    assert kiln.pid.iterm == 0
    assert kiln.pid.pidstats == {}


def test_automatic_restart_waits_for_fresh_sensor_before_restoring_bias(recovery_case, monkeypatch):
    kiln, saved, _ = recovery_case
    persist(saved)
    kiln.reset()
    kiln.board.temp_sensor.ready.return_value = False
    restore = Mock(wraps=kiln.restore_pid_bias)
    monkeypatch.setattr(kiln, 'restore_pid_bias', restore)

    kiln.automatic_restart()

    restore.assert_not_called()
    assert kiln.state == 'IDLE'
    assert kiln.pid.iterm == 0
    assert json.loads(Path(config.automatic_restart_state_file).read_text()) == saved


def test_stopped_firing_does_not_restore_bias_or_enable_heat(recovery_case, monkeypatch):
    kiln, saved, _ = recovery_case
    saved['state'] = 'IDLE'
    persist(saved)
    kiln.reset()
    kiln.output = Mock()
    kiln.output.seconds_on.return_value = 0
    restore = Mock(wraps=kiln.restore_pid_bias)
    monkeypatch.setattr(kiln, 'restore_pid_bias', restore)

    kiln.automatic_restart()

    restore.assert_not_called()
    kiln.output.heat.assert_not_called()
    assert kiln.state == 'IDLE'
    assert kiln.pid.iterm == 0


def test_new_program_and_direct_run_profile_do_not_restore_old_bias(recovery_case, monkeypatch):
    kiln, saved, _ = recovery_case
    kiln.pid.iterm = 72
    restore = Mock(wraps=kiln.restore_pid_bias)
    monkeypatch.setattr(kiln, 'restore_pid_bias', restore)

    kiln.run_profile(Profile(json.dumps(saved['profile_data'])), startat=30,
                     allow_seek=False, recovery=saved)

    restore.assert_not_called()
    assert kiln.pid.iterm == 0
    assert kiln.ramp_control.trim == 0


@pytest.mark.parametrize('failure', ['unready', 'over_temperature', 'sensor_errors'])
def test_restored_bias_cannot_override_real_heater_shutdown(recovery_case, monkeypatch, failure):
    kiln, saved, _ = recovery_case
    assert kiln.restore_pid_bias(saved)
    kiln.output = Mock()
    kiln.output.seconds_on.return_value = 0
    # File durability has separate recovery tests; this test focuses on the
    # actual heater path's fault response without GPIO or real sleeping.
    monkeypatch.setattr(kiln, 'save_automatic_restart_state', Mock())
    monkeypatch.setattr('lib.oven.time.sleep', lambda seconds: None)
    compute = Mock(wraps=kiln.controlled_heat_duty)
    monkeypatch.setattr(kiln, 'controlled_heat_duty', compute)
    if failure == 'unready':
        kiln.board.temp_sensor.ready.return_value = False
    elif failure == 'over_temperature':
        kiln.board.temp_sensor.temperature.return_value = 1240
    else:
        kiln.board.temp_sensor.status.over_error_limit.return_value = True

    RealOven.heat_then_cool(kiln)

    kiln.output.heat.assert_not_called()
    compute.assert_not_called()
    assert kiln.state == 'IDLE'
    assert kiln.pid.iterm == 0


def test_recovered_bias_still_drives_one_thirty_second_pulse(recovery_case):
    kiln, saved, _ = recovery_case
    assert kiln.restore_pid_bias(saved)
    kiln.output = Mock()
    kiln.output.seconds_on.return_value = 0

    RealOven.heat_then_cool(kiln)

    duty = kiln.pid.pidstats['out']
    kiln.output.heat.assert_called_once_with(pytest.approx(30 * duty))
    kiln.output.cool.assert_called_once_with(pytest.approx(30 * (1 - duty)))
    assert 0 < duty < 1
    assert kiln.pid.pidstats['d'] == pytest.approx(0)
    assert kiln.ramp_control.trim == 0
