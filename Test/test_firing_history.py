import json
from types import SimpleNamespace
import pytest
from lib.firing_history import Archive, summarize, aggregate, firing_id


def cfg(**kw):
    return SimpleNamespace(**dict(dict(temp_scale='c',simulate=False,kw_elements=11,kwh_rate=.645,currency_type='₪'),**kw))


def state(t, **kw):
    return dict(dict(timestamp=1000+t,run_started_at=1000,elapsed_seconds=t,runtime=t,
                     state='RUNNING',profile='test',profile_data={'name':'test','data':[[0,100],[3600,300]]},
                     simulate=False,sensor_ready=True,temperature=100+t/12,target=120+t/12,
                     catching_up=False,pidstats={'out':1},
                     energy_accounting={'heater_on_seconds':t,'energy_kwh':11*t/3600,'cost':11*.645*t/3600,'currency_type':'₪'}),**kw)


def points(rate=300,duty=1,duration=360):
    return [dict(timestamp=1000+t,elapsed_seconds=t,program_seconds=0,temperature_c=100+t*rate/3600,
                 target_c=200,sensor_ready=True,state='RUNNING',catching_up=True,session='one',
                 heater_on_seconds=t*duty,duty=duty) for t in range(0,duration+1,10)]


def meta():
    return dict(started_at=1000,finished_at=1360,energy={'heater_on_seconds':360,'energy_kwh':1.1,'cost':.7095,'currency_type':'₪'})


def test_sustained_capacity_uses_elapsed_not_stalled_program_time():
    stats=summarize(points(),meta())
    assert stats['ramps'][0]['max_rate_c_hour']==pytest.approx(300)
    assert stats['ramps'][0]['windows']==2
    assert stats['peak_temperature_c']==130
    assert stats['mean_temperature_c']==pytest.approx(115)
    assert stats['catchup_seconds']==360
    assert stats['mean_tracking_error_c']==pytest.approx(85)


@pytest.mark.parametrize('rate,duty',[(300,.5),(-300,1),(0,1)])
def test_holds_cooling_and_low_power_do_not_define_capacity(rate,duty):
    assert not summarize(points(rate,duty),meta())['ramps']


def test_restart_gap_and_sensor_fault_not_used_for_ramp():
    data=points(duration=180)
    data[8]['sensor_ready']=False
    assert not summarize(data,meta())['ramps']
    data=points(duration=180)
    for p in data[8:]:p['session']='new'
    assert not summarize(data,meta())['ramps']
    data=points(duration=180)[::4]
    assert not summarize(data,meta())['ramps']


def test_temperature_spike_does_not_establish_limit():
    data=points(duration=180)
    data[10]['temperature_c']+=20
    assert not summarize(data,meta())['ramps']


def test_ramp_window_must_fit_inside_its_temperature_band():
    data=points(duration=180)
    for p in data:p['temperature_c']+=40
    assert not summarize(data,meta())['ramps']


def test_log_import_can_use_recorded_pulse_duty():
    data=points()
    for p in data:p['heater_on_seconds']=None
    assert summarize(data,meta())['ramps'][0]['max_rate_c_hour']==pytest.approx(300)


def test_archive_survives_resume_as_one_firing_and_retains_final_totals(tmp_path):
    a=Archive(tmp_path,cfg())
    for t in range(0,191,10):a.capture(state(t))
    a.capture(state(192),force=True)
    b=Archive(tmp_path,cfg())
    b.capture(state(220),force=True)
    b.capture(state(230),finish='completed')
    report=b.overview()
    assert len(report['records'])==1
    assert report['summary']['completed_count']==1
    assert report['summary']['averages']['energy_kwh']['value']==pytest.approx(11*230/3600)
    record=b.detail(firing_id(state(0)))
    assert record['record']['stats']['gaps']==1
    assert record['record']['status']=='completed'
    assert json.loads((tmp_path/'averages.json').read_text())['summary']==report['summary']
    b.reconcile_idle()
    assert b.overview()['records'][0]['status']=='completed'


def test_sampling_limit_and_final_fractional_second_are_preserved(tmp_path):
    a=Archive(tmp_path,cfg())
    for t in range(15):a.capture(state(t))
    a.capture(state(14.5),finish='stopped')
    d=a.detail(firing_id(state(0)))
    assert len(d['samples'])==3
    assert d['record']['stats']['heater_on_seconds']==14.5


def test_power_cut_truncated_last_line_does_not_destroy_new_samples(tmp_path):
    a=Archive(tmp_path,cfg());a.capture(state(0))
    path=tmp_path/firing_id(state(0))/'samples.jsonl'
    with path.open('a') as f:f.write('{"timestamp": 12')
    a=Archive(tmp_path,cfg());a.capture(state(30),force=True)
    assert len(a.detail(firing_id(state(0)))['samples'])==2


def test_interrupted_firing_marked_once_without_recovery(tmp_path):
    a=Archive(tmp_path,cfg());a.capture(state(0));a.capture(state(120),force=True)
    a=Archive(tmp_path,cfg());a.reconcile_idle();a.reconcile_idle()
    r=a.overview();assert r['summary']['finished_count']==1
    assert r['records'][0]['status']=='interrupted'
    assert r['summary']['averages']['elapsed_seconds']['value']==120


def test_new_runs_have_distinct_ids_and_simulation_is_excluded(tmp_path):
    a=Archive(tmp_path,cfg());a.capture(state(0));a.capture(state(30),finish='stopped')
    a.capture(state(40,run_started_at=1040,elapsed_seconds=0,simulate=True),finish='completed')
    assert len(a.records)==2 and len(a.overview()['records'])==1
    with pytest.raises(KeyError):a.detail('../../state.json')
    with pytest.raises(KeyError):a.detail(firing_id(state(40,run_started_at=1040,simulate=True)))


def test_fahrenheit_stored_celsius_for_samples_and_schedule(tmp_path):
    a=Archive(tmp_path,cfg(temp_scale='f'))
    a.capture(state(0,temperature=212,target=392,profile_data={'name':'test','data':[[0,212],[3600,392]]}),force=True)
    d=a.detail(firing_id(state(0)))
    assert d['samples'][0]['temperature_c']==pytest.approx(100)
    assert d['record']['profile_data']['data'][1][1]==pytest.approx(200)


def test_averages_exclude_current_run_and_currency_and_power_are_separated():
    s=summarize(points(),meta())
    records=[dict(id='one',status='completed',stats=s,kw_elements=11),
             dict(id='two',status='RUNNING',stats=dict(s,energy_kwh=100),kw_elements=11),
             dict(id='three',status='stopped',stats=dict(s,currency_type='$',cost=5,
                  ramps=[dict(s['ramps'][0],max_rate_c_hour=900)]),kw_elements=22)]
    a=aggregate(records,11)
    assert a['averages']['energy_kwh']==dict(value=1.1,count=2)
    assert len(a['costs'])==2
    assert a['ramps'][0]['max_rate_c_hour']==pytest.approx(300)
    assert a['ramps'][0]['firing_count']==2


def test_archive_failure_is_visible_without_resetting_oven(monkeypatch):
    import config
    from lib.oven import Oven
    kiln=Oven()
    class Broken:
        error=None
        def capture(self,*args,**kwargs):raise OSError('disk full')
    kiln.firing_history=Broken()
    kiln.record_history()
    assert 'disk full' in kiln.firing_history.error


@pytest.mark.parametrize('path,key',[('storage/firings','kiln_profiles_directory'),('storage/firings/state.json','automatic_restart_state_file')])
def test_history_paths_are_reserved(path,key,tmp_path):
    from lib.settings_store import contained_path, SettingsError
    with pytest.raises(SettingsError):contained_path(tmp_path,path,key)


def test_idle_after_crash_recovers_latest_energy_from_durable_samples(tmp_path):
    a=Archive(tmp_path,cfg());a.capture(state(0));a.capture(state(10));a.capture(state(20))
    # Metadata may lag the append journal by up to one minute.
    b=Archive(tmp_path,cfg());b.reconcile_idle()
    assert b.overview()['records'][0]['stats']['energy_kwh']==pytest.approx(11*20/3600)


def test_clear_removes_readings_and_resets_statistics_across_restart(tmp_path):
    a=Archive(tmp_path,cfg())
    for t in range(0,191,10):a.capture(state(t))
    a.capture(state(200),finish='completed')
    identity=firing_id(state(0))
    assert a.overview()['summary']['ramps']
    assert a.clear_finished(a.clear_review()['revision'])==[identity]
    assert not (tmp_path/identity).exists()
    assert a.current_id is None and not a.current_points
    assert not list(tmp_path.glob('.clear-*'))
    saved=json.loads((tmp_path/'averages.json').read_text())
    assert saved['summary']['finished_count']==0
    assert saved['summary']['averages']['energy_kwh']=={'value':None,'count':0}
    assert saved['summary']['ramps']==[]
    b=Archive(tmp_path,cfg())
    assert not b.overview()['records']
    with pytest.raises(KeyError):b.detail(identity)
    b.capture(state(0,run_started_at=2000))
    assert b.overview()['summary']['active_count']==1


@pytest.mark.parametrize('active',['RUNNING','PAUSED'])
def test_clear_keeps_active_records_other_mode_and_unrelated_files(tmp_path,active):
    a=Archive(tmp_path/'firings',cfg());a.capture(state(0),finish='stopped')
    review=a.clear_review()
    a.capture(state(20,run_started_at=1020,simulate=True),finish='completed')
    a.capture(state(30,run_started_at=1030,state=active))
    identity=firing_id(state(30,run_started_at=1030,state=active))
    keep={p:p.read_bytes() for p in (a.root/identity).iterdir()}
    recovery=tmp_path/'state.json';recovery.write_text('{"state":"RUNNING"}')
    program=tmp_path/'program.json';program.write_text('{"name":"test"}')
    assert len(a.clear_finished(review['revision']))==1
    assert len(a.records)==2 and a.current_id==identity and a.current_points
    assert a.overview()['summary']['active_count']==1
    assert all(p.read_bytes()==data for p,data in keep.items())
    assert recovery.read_text()=='{"state":"RUNNING"}'
    assert program.read_text()=='{"name":"test"}'
    assert Archive(a.root,cfg()).detail(identity)['record']['status']==active


def test_clear_rejects_newly_finished_record_without_deleting_anything(tmp_path):
    from lib.firing_history import HistoryChanged
    a=Archive(tmp_path,cfg());a.capture(state(0),finish='stopped')
    review=a.clear_review()
    a.capture(state(20,run_started_at=1020),finish='completed')
    before={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    with pytest.raises(HistoryChanged):a.clear_finished(review['revision'])
    assert len(a.records)==2
    assert all(p.read_bytes()==data for p,data in before.items())


def test_clear_rejects_symlink_before_removing_any_records(tmp_path):
    import shutil
    a=Archive(tmp_path/'firings',cfg());a.capture(state(0),finish='completed')
    a.capture(state(20,run_started_at=1020),finish='stopped')
    bad=a.root/firing_id(state(20,run_started_at=1020))
    outside=tmp_path/'outside';shutil.move(str(bad),outside)
    bad.symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError):a.clear_finished(a.clear_review()['revision'])
    assert (a.root/firing_id(state(0))/'samples.jsonl').exists()
    assert (outside/'samples.jsonl').exists()
    assert len(a.records)==2


def test_interrupted_clear_finishes_cleanup_without_resurrecting_history(tmp_path,monkeypatch):
    import lib.firing_history as history
    a=Archive(tmp_path,cfg());a.capture(state(0),finish='completed')
    remove=history.shutil.rmtree
    monkeypatch.setattr(history.shutil,'rmtree',lambda *args:(_ for _ in ()).throw(OSError('interruption')))
    with pytest.raises(OSError):a.clear_finished(a.clear_review()['revision'])
    assert not a.records and list(tmp_path.glob('.clear-*'))
    monkeypatch.setattr(history.shutil,'rmtree',remove)
    b=Archive(tmp_path,cfg())
    assert not b.records and not list(tmp_path.glob('.clear-*'))


def test_partial_clear_failure_keeps_remaining_records_and_updates_averages(tmp_path,monkeypatch):
    import lib.firing_history as history
    a=Archive(tmp_path,cfg());a.capture(state(0),finish='completed')
    a.capture(state(20,run_started_at=1020),finish='stopped')
    second=firing_id(state(20,run_started_at=1020));replace=history.os.replace
    def fail_second(source,destination):
        if source==tmp_path/second:raise OSError('disk error')
        return replace(source,destination)
    monkeypatch.setattr(history.os,'replace',fail_second)
    with pytest.raises(OSError):a.clear_finished(a.clear_review()['revision'])
    assert list(a.records)==[second]
    assert json.loads((tmp_path/'averages.json').read_text())['summary']['finished_count']==1
    assert list(Archive(tmp_path,cfg()).records)==[second]


def test_clear_api_requires_review_token_origin_confirmation_and_revision(tmp_path):
    import bottle,io
    from lib.firing_history import install_api
    a=Archive(tmp_path,cfg());a.capture(state(0),finish='completed')
    app=bottle.Bottle();install_api(app,a)
    def request(path='/api/firings',body=None,token=None,origin='http://kiln:8081'):
        payload=json.dumps(body or {}).encode();statuses=[]
        env={'REQUEST_METHOD':'POST' if body is not None else 'GET','PATH_INFO':path,
             'SERVER_NAME':'kiln','SERVER_PORT':'8081','SERVER_PROTOCOL':'HTTP/1.1',
             'HTTP_HOST':'kiln:8081','wsgi.url_scheme':'http','wsgi.input':io.BytesIO(payload),
             'wsgi.errors':io.StringIO(),'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(payload)),'HTTP_ORIGIN':origin}
        if token:env['HTTP_X_KILN_HISTORY']=token
        raw=b''.join(app(env,lambda status,headers,*args:statuses.append(status)))
        try:result=json.loads(raw)
        except ValueError:result=raw.decode()
        return int(statuses[0].split()[0]),result
    code,report=request();assert code==200 and report['clear']['count']==1
    token=report['clear']['token'];body=dict(confirm='clear_finished_firings',revision=report['clear']['revision'])
    endpoint='/api/firings/clear'
    assert request(endpoint,body)[0]==403
    assert request(endpoint,body,token,'http://other')[0]==403
    assert request(endpoint,{},token)[0]==400
    assert request(endpoint,dict(body,revision='stale'),token)[0]==409
    assert len(a.records)==1
    code,result=request(endpoint,body,token)
    assert code==200 and result['cleared']==1 and result['clear']['count']==0
    assert result['summary']['finished_count']==0
    assert request('/api/firings/'+firing_id(state(0)))[0]==404
