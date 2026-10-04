import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import config
from lib.oven import Output, Oven, Profile


@pytest.fixture
def metered(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'simulate', True)
    monkeypatch.setattr(config, 'seek_start', False)
    monkeypatch.setattr(config, 'kw_elements', 11.0)
    monkeypatch.setattr(config, 'kwh_rate', .645)
    monkeypatch.setattr(config, 'currency_type', '₪')
    monkeypatch.setattr(config, 'automatic_restart_state_file', str(tmp_path/'state.json'))
    clock=SimpleNamespace(now=0.0)
    monkeypatch.setattr('lib.oven.time.monotonic', lambda:clock.now)
    def sleep(seconds):clock.now+=seconds
    monkeypatch.setattr('lib.oven.time.sleep', sleep)
    gpio=SimpleNamespace(value=False, switch_to_output=Mock())
    monkeypatch.setattr('lib.oven.digitalio.DigitalInOut',lambda pin:gpio)
    output=Output()
    kiln=Oven()
    kiln.output=output
    kiln.run_profile(Profile(json.dumps({'name':'energy test','data':[[0,20],[7200,200]]})),allow_seek=False)
    return kiln,output,clock


@pytest.mark.parametrize('duty',[0,.2,1])
def test_cost_uses_pulse_duration_not_on_flag(metered,duty):
    kiln,output,clock=metered
    for _ in range(5):
        if duty:output.heat(2*duty)
        output.cool(2*(1-duty))
        kiln.heat=1 if duty else 0
        kiln.update_cost()
    state=kiln.get_state()['energy_accounting']
    assert state['heater_on_seconds']==pytest.approx(10*duty)
    assert state['energy_kwh']==pytest.approx(11*10*duty/3600)
    assert state['cost']==pytest.approx(11*.645*10*duty/3600)


def test_one_hour_on_costs_7_095_shekels_even_while_catching_up(metered):
    kiln,output,clock=metered
    kiln.catching_up=True
    kiln.runtime=0
    output.heat(3600)
    state=kiln.get_state()['energy_accounting']
    assert state['energy_kwh']==11
    assert state['cost']==pytest.approx(7.095)
    output.cool(3600)
    assert kiln.get_state()['energy_accounting']==state


def test_live_pulse_readings_do_not_double_charge(metered,monkeypatch):
    kiln,output,clock=metered
    def sleep(seconds):
        if seconds:
            clock.now+=seconds/2
            a=kiln.get_state()['energy_accounting']
            b=kiln.get_state()['energy_accounting']
            assert a==b
            assert a['heater_on_seconds']==pytest.approx(seconds/2)
            clock.now+=seconds/2
    monkeypatch.setattr('lib.oven.time.sleep',sleep)
    output.heat(2)
    assert kiln.get_state()['energy_accounting']['heater_on_seconds']==2


def test_pause_and_recovery_preserve_energy_without_charging_downtime(metered):
    kiln,output,clock=metered
    kiln.state='PAUSED'
    output.heat(15)
    kiln.get_state()
    kiln.state='RUNNING'
    kiln.save_state()
    output.cool(600)
    recovery=Oven()
    recovery.automatic_restart()
    assert recovery.state=='RUNNING'
    assert recovery.get_state()['energy_accounting']['heater_on_seconds']==15
    recovery._simulated_on_seconds=5
    assert recovery.get_state()['energy_accounting']['heater_on_seconds']==20
    assert recovery.cost==pytest.approx(11*.645*20/3600)


def test_stop_during_pulse_keeps_final_cost_and_next_run_starts_zero(metered,monkeypatch):
    kiln,output,clock=metered
    def sleep(seconds):
        if seconds:
            clock.now+=.4
            kiln.abort_run()
            clock.now+=seconds-.4
    monkeypatch.setattr('lib.oven.time.sleep',sleep)
    output.heat(2)
    assert kiln.state=='IDLE'
    assert output.heater.value==output.off
    assert kiln.get_state()['last_firing_energy']['heater_on_seconds']==pytest.approx(.4)
    rebooted=Oven()
    assert rebooted.last_firing_energy['heater_on_seconds']==pytest.approx(.4)
    kiln.run_profile(Profile(json.dumps({'name':'next','data':[[0,20],[60,30]]})),allow_seek=False)
    assert kiln.get_state()['energy_accounting']['cost']==0


def test_failed_pulse_counts_only_time_before_switching_off(metered,monkeypatch):
    kiln,output,clock=metered
    def sleep(seconds):
        if seconds:
            clock.now+=.3
            raise RuntimeError('interrupted')
    monkeypatch.setattr('lib.oven.time.sleep',sleep)
    with pytest.raises(RuntimeError):output.heat(2)
    assert output.heater.value==output.off
    assert kiln.get_state()['energy_accounting']['heater_on_seconds']==pytest.approx(.3)


def test_legacy_cost_is_not_presented_as_complete(metered):
    kiln,output,clock=metered
    kiln.restore_energy({'cost':999})
    state=kiln.get_state()['energy_accounting']
    assert state['cost']==0
    assert state['history_incomplete']
