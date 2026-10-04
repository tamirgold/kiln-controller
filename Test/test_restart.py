import json
import os
import time
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import config
from lib.oven import Oven, Profile, RealOven, TempSensorReal, TempTracker

@pytest.fixture
def kiln(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'simulate', True)
    monkeypatch.setattr(config, 'automatic_restart_state_file', str(tmp_path/'state.json'))
    monkeypatch.setattr(config, 'seek_start', False)
    k = Oven()
    k.run_profile(Profile(json.dumps({'name':'test-celsius','data':[[0,20],[600,150],[1200,150]]})), startat=3.25)
    k.cost = 1.25
    k.save_state()
    return k

def saved():
    with open(config.automatic_restart_state_file) as f: return json.load(f)

def write(data):
    with open(config.automatic_restart_state_file, 'w') as f: json.dump(data,f)

def test_resume_exact_progress_and_celsius_profile(kiln):
    recovery=Oven()
    assert recovery.should_i_automatic_restart()
    recovery.automatic_restart()
    assert recovery.state == 'RUNNING'
    assert recovery.runtime == 195
    assert recovery.cost == 1.25
    assert recovery.profile.data == [[0,20],[600,150],[1200,150]]
    assert recovery.profile.get_target_temperature(600) == 150

@pytest.mark.parametrize('change', [
    {'saved_at':time.time()-901}, {'saved_at':time.time()+120},
    {'state':'IDLE'}, {'state':'PAUSED'}, {'runtime':-1}, {'runtime':float('nan')},
    {'runtime':1200}, {'runtime':True}, {'cost':-1}, {'temp_scale':'f'},
    {'simulate':False}, {'profile_data':{'name':'wrong','data':[[0,20],[600,100]]}},
    {'profile_data':{'name':'test-celsius','data':[[0,20],[0,40]]}},
])
def test_invalid_or_ineligible_state_does_not_resume(kiln,change):
    data=saved(); data.update(change); write(data)
    recovery=Oven()
    assert not recovery.should_i_automatic_restart()
    recovery.automatic_restart()
    assert recovery.state == 'IDLE'

def test_corrupt_state_keeps_controller_idle(kiln):
    with open(config.automatic_restart_state_file,'w') as f: f.write('{broken')
    recovery=Oven()
    assert not recovery.should_i_automatic_restart()
    recovery.automatic_restart()
    assert recovery.state=='IDLE'

def test_stop_cancels_restart(kiln):
    kiln.abort_run()
    assert saved()['state']=='IDLE'
    assert not Oven().should_i_automatic_restart()

def test_failed_atomic_replace_preserves_previous_state(kiln,monkeypatch):
    before=saved()
    monkeypatch.setattr('lib.oven.os.replace',Mock(side_effect=OSError('simulated disk error')))
    kiln.runtime=240
    with pytest.raises(OSError): kiln.save_state()
    assert saved()==before
    assert list(__import__('pathlib').Path(config.automatic_restart_state_file).parent.glob('.kiln-state-*'))==[]

def test_no_heat_without_ready_sensor(kiln,monkeypatch):
    # Exercise the real control path with an output spy; no GPIO is driven.
    monkeypatch.setattr('lib.oven.time.sleep',lambda seconds:None)
    k=RealOven.__new__(RealOven)
    k.output=Mock()
    k.output.seconds_on.return_value=0
    k.board=SimpleNamespace(temp_sensor=SimpleNamespace(ready=lambda:False,temperature=lambda:20))
    Oven.__init__(k)
    k.state='RUNNING'
    k.heat_then_cool()
    k.output.heat.assert_not_called()
    assert k.state=='IDLE'

def test_recovery_waits_for_sensor_without_losing_saved_progress(kiln,monkeypatch):
    monkeypatch.setattr(config,'simulate',False)
    data=saved(); data['simulate']=False; write(data)
    recovery=Oven()
    recovery.board=SimpleNamespace(temp_sensor=SimpleNamespace(ready=lambda:False))
    recovery.automatic_restart()
    assert recovery.state=='IDLE'
    assert saved()['state']=='RUNNING'

def test_sensor_requires_full_window_and_fresh_readings():
    sensor=TempSensorReal.__new__(TempSensorReal)
    sensor.time_step=2
    sensor.last_good_read=None
    sensor.temptracker=TempTracker()
    sensor.status=SimpleNamespace(over_error_limit=lambda:False)
    assert not sensor.ready()
    for _ in range(sensor.temptracker.size): sensor.temptracker.add(0)
    sensor.last_good_read=time.monotonic()
    assert sensor.ready() # Zero Celsius is a valid reading.
    sensor.last_good_read-=5
    assert not sensor.ready()

def test_profile_end_is_safe(kiln):
    assert kiln.profile.get_target_temperature(1200)==0

def test_elapsed_firing_time_survives_restart_and_catch_up(kiln):
    kiln.run_started_at = time.time() - 49 * 3600
    kiln.catching_up = True
    kiln.save_state()
    recovery = Oven()
    recovery.automatic_restart()
    assert recovery.run_started_at == kiln.run_started_at
    state = recovery.get_state()
    assert 49 * 3600 <= state['elapsed_seconds'] < 49 * 3600 + 3
    assert state['runtime'] == 195
    assert state['elapsed_origin_known']

def test_legacy_state_does_not_invent_original_start(kiln):
    data = saved()
    del data['run_started_at']
    write(data)
    recovery = Oven()
    recovery.automatic_restart()
    assert recovery.state == 'RUNNING'
    assert not recovery.elapsed_origin_known

def test_heat_rate_uses_elapsed_time_even_with_frozen_program(kiln):
    kiln.heat_rate_temps = []
    kiln.runtime = 100
    kiln.set_heat_rate(1000, 100)
    kiln.set_heat_rate(1030, 105)
    assert kiln.heat_rate == 600
    kiln.set_heat_rate(1030.1, 10000)
    assert kiln.heat_rate == 600  # Repeated status polls cannot skew the rate.
