"""Exercise the ramp observer through the production control and output paths."""
import datetime
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import config
from lib.oven import Oven, Output, Profile, RealOven, SimulatedOven, TempSensorReal, TempTracker
from lib.settings_store import SCHEMA, SettingsError, Store, atomic_json, load_overrides, validate


@pytest.fixture
def kiln(tmp_path, monkeypatch):
    for name, value in {
        'automatic_restart_state_file': str(tmp_path / 'state.json'),
        'automatic_ramp_control': True, 'automatic_restarts': True,
        'automatic_restart_window': 25, 'require_synced_clock_for_restart': False,
        'simulate': False, 'seek_start': False, 'temp_scale': 'c',
        'sensor_time_wait': 30, 'thermocouple_offset': 0,
        'pid_control_window': 10, 'catch_up_tolerance': 3,
        'throttle_below_temp': 0, 'throttle_percent': 100,
        'emergency_shutoff_temp': 1240, 'ignore_temp_too_high': False,
        'ignore_tc_too_many_errors': False, 'kw_elements': 8, 'kwh_rate': .645,
    }.items():
        monkeypatch.setattr(config, name, value)
    sensor = SimpleNamespace(temperature=Mock(return_value=130.0),
                             cycle_temperature=Mock(return_value=130.0),
                             ready=Mock(return_value=True),
                             status=SimpleNamespace(over_error_limit=Mock(return_value=False)))
    oven = Oven()
    oven.board = SimpleNamespace(temp_sensor=sensor)
    oven.run_profile(Profile(json.dumps({
        'name': 'automatic ramp integration',
        'data': [[0, 100], [3600, 160], [4200, 160], [7800, 100]],
    })), startat=30, allow_seek=False)
    return oven


def set_temperature(kiln, median, mean=None):
    kiln.board.temp_sensor.temperature.return_value = median
    kiln.board.temp_sensor.cycle_temperature.return_value = median if mean is None else mean


def stub_pid(kiln, monkeypatch, duty=.5, integral_delta=0):
    def compute(target, temperature, now):
        kiln.pid.iterm += integral_delta
        kiln.pid.pidstats = dict(out=duty, i=kiln.pid.iterm)
        return duty
    compute = Mock(side_effect=compute)
    monkeypatch.setattr(kiln.pid, 'compute', compute)
    return compute


def learn_slow_ramp(kiln, monkeypatch, duration=600, duty=.5):
    """A 12 C/hour trend within the unchanged target's temperature window."""
    compute = stub_pid(kiln, monkeypatch, duty)
    epoch = kiln.pid.lastNow
    for elapsed in range(0, duration + 1, 30):
        set_temperature(kiln, 128 + elapsed * 12 / 3600)
        kiln.controlled_heat_duty(epoch + datetime.timedelta(seconds=elapsed + 30), elapsed)
    assert kiln.ramp_control.snapshot()['measured_rate'] == pytest.approx(12)
    assert kiln.ramp_control.trim > 0
    return compute


@pytest.fixture
def metered(kiln, monkeypatch):
    clock = SimpleNamespace(now=900.0)
    monkeypatch.setattr('lib.oven.time.monotonic', lambda: clock.now)
    monkeypatch.setattr('lib.oven.time.sleep', lambda seconds: setattr(clock, 'now', clock.now + seconds))
    gpio = SimpleNamespace(value=False, switch_to_output=Mock())
    monkeypatch.setattr('lib.oven.digitalio.DigitalInOut', lambda pin: gpio)
    output = Output()
    kiln.output = output
    kiln._energy_output_baseline = output.seconds_on()
    heat, cool = output.heat, output.cool
    output.heat, output.cool = Mock(wraps=heat), Mock(wraps=cool)
    return kiln, output, clock


def test_pid_keeps_median_while_observer_uses_full_cycle_mean_and_one_offset(kiln, monkeypatch):
    monkeypatch.setattr(config, 'thermocouple_offset', 7)
    sensor = TempSensorReal.__new__(TempSensorReal)
    sensor.temptracker = TempTracker()
    sensor.temptracker.temps = [90.0, 100.0, 140.0]
    sensor.ready = Mock(return_value=True)
    kiln.board.temp_sensor = sensor
    kiln.target = 107
    compute = stub_pid(kiln, monkeypatch)

    kiln.controlled_heat_duty(kiln.pid.lastNow + datetime.timedelta(seconds=30), 1000)

    assert sensor.temperature() == 100
    assert sensor.cycle_temperature() == 110
    assert compute.call_args.args[1] == 107
    assert kiln.ramp_control.samples == [(1000, 117)]
    assert kiln.get_state()['temperature'] == 107


def test_sensor_without_cycle_mean_uses_offset_median_once(kiln, monkeypatch):
    monkeypatch.setattr(config, 'thermocouple_offset', 7)
    del kiln.board.temp_sensor.cycle_temperature
    stub_pid(kiln, monkeypatch)

    kiln.controlled_heat_duty(kiln.pid.lastNow + datetime.timedelta(seconds=30), 1000)

    assert kiln.ramp_control.samples == [(1000, 137)]


def test_actual_elapsed_trend_corrects_duty_without_advancing_frozen_program(kiln, monkeypatch):
    original = (kiln.runtime, kiln.target, kiln.start_time, kiln.run_started_at,
                list(kiln.profile.data), kiln.totaltime)
    kiln.catching_up = True

    learn_slow_ramp(kiln, monkeypatch)

    report = kiln.get_state()['ramp_control']
    assert report['requested_rate'] == 60
    assert report['measured_rate'] == pytest.approx(12)
    assert report['applied_trim_percent'] > 0
    assert report['correction_count'] > 0
    assert .5 < kiln.pid.pidstats['out'] <= .6
    assert (kiln.runtime, kiln.target, kiln.start_time, kiln.run_started_at,
            kiln.profile.data, kiln.totaltime) == original
    assert kiln.catching_up
    # Status requests have no effect on the observer or correction cadence.
    for _ in range(20):
        kiln.get_state()
    assert kiln.ramp_control.snapshot() == report


def test_corrected_duty_drives_30_second_relay_cycle_and_metered_energy(metered, monkeypatch):
    kiln, output, clock = metered
    learn_slow_ramp(kiln, monkeypatch)
    clock.now = 630
    started = clock.now

    RealOven.heat_then_cool(kiln)

    duty = kiln.pid.pidstats['out']
    assert duty > kiln.pid.pidstats['base_out'] == .5
    on = output.heat.call_args.args[0]
    off = output.cool.call_args.args[0]
    assert on == pytest.approx(30 * duty)
    assert on + off == pytest.approx(30)
    assert clock.now - started == pytest.approx(30)
    state = kiln.get_state()
    assert state['pidstats']['out'] == pytest.approx(duty)
    assert state['ramp_control']['output_percent'] == pytest.approx(100 * duty)
    assert state['energy_accounting']['heater_on_seconds'] == pytest.approx(on)
    assert state['energy_accounting']['energy_kwh'] == pytest.approx(8 * on / 3600)
    assert state['energy_accounting']['cost'] == pytest.approx(8 * on / 3600 * .645)


def test_simulator_observer_uses_control_cycle_time_when_program_is_waiting(kiln, monkeypatch):
    monkeypatch.setattr(config, 'simulate', True)
    monkeypatch.setattr('lib.oven.time.sleep', lambda seconds: None)
    simulated = SimulatedOven.__new__(SimulatedOven)
    simulated.speedup_factor = 60
    simulated.board = kiln.board
    Oven.__init__(simulated)
    simulated.run_profile(kiln.profile, startat=30, allow_seek=False)
    simulated.catching_up = True
    simulated.heating_energy = Mock()
    simulated.temp_changes = Mock()
    simulated.p_heat, simulated.t_h, simulated.p_ho, simulated.t, simulated.p_env = 8000, 130, 0, 130, 0
    stub_pid(simulated, monkeypatch)

    for elapsed in range(0, 391, 30):
        set_temperature(simulated, 128 + elapsed * 12 / 3600)
        simulated.heat_then_cool()

    report = simulated.ramp_control.snapshot()
    assert simulated.runtime == 1800
    assert simulated._ramp_elapsed == 420
    assert report['measured_rate'] == pytest.approx(12)
    assert report['applied_trim_percent'] > 0
    assert simulated.heating_energy.call_args.args[0] == simulated.pid.pidstats['out']


@pytest.mark.parametrize('runtime,state,phase,rate', [
    (3600, 'RUNNING', 'hold', 0), (4200, 'RUNNING', 'cooling', -60),
    (1800, 'PAUSED', 'paused', 0),
])
def test_new_segment_and_pause_discard_previous_ramp_learning(kiln, monkeypatch, runtime, state, phase, rate):
    learn_slow_ramp(kiln, monkeypatch)
    kiln.runtime, kiln.state = runtime, state
    kiln.update_target_temp()
    set_temperature(kiln, kiln.target)

    output = kiln.controlled_heat_duty(kiln.pid.lastNow + datetime.timedelta(seconds=30), 630)

    report = kiln.ramp_control.snapshot()
    assert report['phase'] == phase
    assert report['requested_rate'] == rate
    assert report['measured_rate'] is None
    assert report['trim_percent'] == report['applied_trim_percent'] == 0
    assert report['correction_count'] == 0
    assert output == .5


def test_disabling_automatic_control_restores_ordinary_pid_immediately(kiln, monkeypatch):
    learn_slow_ramp(kiln, monkeypatch)
    monkeypatch.setattr(config, 'automatic_ramp_control', False)

    output = kiln.controlled_heat_duty(kiln.pid.lastNow + datetime.timedelta(seconds=30), 630)

    assert output == .5
    assert kiln.ramp_control.snapshot()['status'] == 'disabled'
    assert kiln.ramp_control.trim == 0


def test_reset_clears_observer_and_correction(kiln, monkeypatch):
    learn_slow_ramp(kiln, monkeypatch)

    kiln.reset()

    assert kiln.ramp_control.samples == []
    assert kiln.ramp_control.trim == 0
    assert kiln.ramp_control.snapshot()['correction_count'] == 0
    assert kiln._ramp_elapsed == 0


def test_recovery_preserves_program_and_energy_but_collects_fresh_ramp_measurements(kiln, monkeypatch):
    learn_slow_ramp(kiln, monkeypatch)
    kiln._simulated_on_seconds = 120
    kiln.save_state()
    saved = json.loads(Path(config.automatic_restart_state_file).read_text())
    assert saved['ramp_control']['trim_percent'] > 0
    recovered = Oven()
    recovered.board = kiln.board

    recovered.automatic_restart()

    assert recovered.state == 'RUNNING'
    assert recovered.runtime == kiln.runtime
    assert recovered.run_started_at == kiln.run_started_at
    assert recovered.profile.data == kiln.profile.data
    assert recovered.get_state()['energy_accounting'] == kiln.get_state()['energy_accounting']
    assert recovered.ramp_control.samples == []
    assert recovered.ramp_control.trim == 0
    stub_pid(recovered, monkeypatch)
    recovered.controlled_heat_duty(recovered.pid.lastNow + datetime.timedelta(seconds=30), 10000)
    assert recovered.ramp_control.snapshot()['status'] == 'collecting'
    assert recovered.ramp_control.snapshot()['measured_rate'] is None
    assert recovered.ramp_control.snapshot()['applied_trim_percent'] == 0


@pytest.mark.parametrize('temperature,expected', [(110, 1), (150, 0)])
def test_real_pid_hard_temperature_decisions_override_learned_trim(kiln, monkeypatch, temperature, expected):
    with monkeypatch.context() as learning:
        learn_slow_ramp(kiln, learning)
    set_temperature(kiln, temperature)

    output = kiln.controlled_heat_duty(kiln.pid.lastNow + datetime.timedelta(seconds=30), 630)

    assert output == expected
    assert kiln.pid.pidstats['base_out'] == expected
    assert kiln.ramp_control.snapshot()['applied_trim_percent'] == 0


def test_new_trim_never_exceeds_low_temperature_output_limit(kiln, monkeypatch):
    monkeypatch.setattr(config, 'throttle_below_temp', 150)
    monkeypatch.setattr(config, 'throttle_percent', 40)
    learn_slow_ramp(kiln, monkeypatch, duty=.39)

    assert kiln.pid.pidstats['out'] <= .4
    assert kiln.ramp_control.snapshot()['applied_trim_percent'] <= 1 + 1e-9


def test_low_temperature_pid_behavior_inside_window_is_preserved(kiln, monkeypatch):
    monkeypatch.setattr(config, 'throttle_below_temp', 150)
    monkeypatch.setattr(config, 'throttle_percent', 40)
    stub_pid(kiln, monkeypatch, duty=.6)

    output = kiln.controlled_heat_duty(kiln.pid.lastNow + datetime.timedelta(seconds=30), 0)

    assert output == .6


@pytest.mark.parametrize('base,delta,trim', [(.95, 2, .08), (.05, -2, -.08)])
def test_inner_integral_does_not_wind_up_when_trim_saturates_output(kiln, monkeypatch, base, delta, trim):
    learn_slow_ramp(kiln, monkeypatch)
    kiln.ramp_control.trim = trim
    stub_pid(kiln, monkeypatch, duty=base, integral_delta=delta)
    before = kiln.pid.iterm

    output = kiln.controlled_heat_duty(kiln.pid.lastNow + datetime.timedelta(seconds=30), 630)

    assert output == (1 if trim > 0 else 0)
    assert kiln.pid.pidstats['integral_held']
    assert kiln.pid.iterm == before
    assert kiln.pid.pidstats['i'] == before


@pytest.mark.parametrize('enabled,base,delta', [(True, 1, 2), (True, 0, -2), (False, 1, 2)])
def test_no_new_integral_behavior_without_applied_ramp_trim(kiln, monkeypatch, enabled, base, delta):
    monkeypatch.setattr(config, 'automatic_ramp_control', enabled)
    stub_pid(kiln, monkeypatch, duty=base, integral_delta=delta)
    before = kiln.pid.iterm

    kiln.controlled_heat_duty(kiln.pid.lastNow + datetime.timedelta(seconds=30), 0)

    assert kiln.ramp_control.snapshot()['applied_trim_percent'] == 0
    assert not kiln.pid.pidstats['integral_held']
    assert kiln.pid.iterm == before + delta


@pytest.mark.parametrize('failure', ['not_ready', 'over_temperature', 'sensor_errors'])
def test_real_heat_path_shuts_down_before_pid_or_trim_on_fault(metered, monkeypatch, failure):
    kiln, output, clock = metered
    compute = learn_slow_ramp(kiln, monkeypatch)
    compute.reset_mock()
    if failure == 'not_ready':
        kiln.board.temp_sensor.ready.return_value = False
    elif failure == 'over_temperature':
        set_temperature(kiln, 1240)
    else:
        kiln.board.temp_sensor.status.over_error_limit.return_value = True

    RealOven.heat_then_cool(kiln)

    output.heat.assert_not_called()
    compute.assert_not_called()
    assert kiln.state == 'IDLE'
    assert kiln.ramp_control.trim == 0
    assert kiln.ramp_control.samples == []
    assert output.heater.value == output.off
    assert json.loads(Path(config.automatic_restart_state_file).read_text())['state'] == 'IDLE'


@pytest.fixture
def ramp_settings(tmp_path, monkeypatch):
    for key in ('KILN_SETTINGS_FILE', 'KILN_SIMULATE', 'KILN_PORT', 'KILN_STATE_FILE'):
        monkeypatch.delenv(key, raising=False)
    namespace = dict(vars(config), __file__=str(tmp_path / 'config.py'),
                     automatic_restart_state_file=str(tmp_path / 'state.json'),
                     kiln_profiles_directory=str(tmp_path / 'storage/profiles'),
                     automatic_ramp_control=False, simulate=True)
    Path(namespace['kiln_profiles_directory']).mkdir(parents=True)
    return Store(SimpleNamespace(**namespace)), namespace


@pytest.mark.parametrize('value', [0, 1, 'true', 'false', None])
def test_automatic_ramp_setting_requires_a_boolean(ramp_settings, value):
    store, _ = ramp_settings
    with pytest.raises(SettingsError):
        validate({'automatic_ramp_control': value}, store.current, store.root)


def test_automatic_ramp_setting_persists_without_changing_relay_or_pid(ramp_settings):
    store, namespace = ramp_settings
    assert next(field for field in SCHEMA if field['key'] == 'automatic_ramp_control')['type'] == 'boolean'
    store.save({'automatic_ramp_control': True}, store.revision())
    assert not store.current['automatic_ramp_control']
    store.apply(store.revision())
    fresh = dict(namespace)
    load_overrides(fresh)

    assert fresh['automatic_ramp_control'] is True
    for key in ('sensor_time_wait', 'pid_kp', 'pid_ki', 'pid_kd', 'catch_up_tolerance'):
        assert fresh[key] == namespace[key]


@pytest.mark.parametrize('document', ['active', 'pending'])
def test_old_settings_inherit_disabled_ramp_control_without_losing_tuning(ramp_settings, document):
    store, namespace = ramp_settings
    previous = dict(store.current, pid_kp=8, pid_ki=44.4444444444, pid_kd=100,
                    sensor_time_wait=30, catch_up_tolerance=2.7777777778)
    del previous['automatic_ramp_control']
    atomic_json(getattr(store, document), {'version': 1, 'values': previous})
    if document == 'pending':
        assert store.desired()['automatic_ramp_control'] is False
        store.apply(store.revision())
    fresh = dict(namespace)
    load_overrides(fresh)

    assert fresh['automatic_ramp_control'] is False
    for key in ('sensor_time_wait', 'pid_kp', 'pid_ki', 'pid_kd', 'catch_up_tolerance'):
        assert fresh[key] == previous[key]
