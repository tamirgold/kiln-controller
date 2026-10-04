import ast
import copy
import io
import json
import logging
from pathlib import Path
from types import SimpleNamespace
import threading
import socket
import bottle
import pytest
import config
from lib.settings_store import Store,SettingsError,serialize,validate,SCHEMA,atomic_json,load_overrides
from lib.settings_api import install

@pytest.fixture
def settings(tmp_path,monkeypatch):
    for key in ('KILN_SETTINGS_FILE','KILN_SIMULATE','KILN_PORT','KILN_STATE_FILE'):monkeypatch.delenv(key,raising=False)
    namespace=dict(vars(config));namespace['__file__']=str(tmp_path/'config.py')
    namespace['automatic_restart_state_file']=str(tmp_path/'state.json')
    namespace['kiln_profiles_directory']=str(tmp_path/'storage/profiles')
    namespace['simulate']=True
    Path(namespace['kiln_profiles_directory']).mkdir(parents=True)
    atomic_json(Path(namespace['kiln_profiles_directory'])/'one.json',{'name':'one','data':[[0,20],[3600,200]],'temp_units':'c'})
    atomic_json(tmp_path/'state.json',{'state':'IDLE','cost':12})
    module=SimpleNamespace(**namespace)
    return Store(module),module

def test_schema_covers_all_config_values():
    names=set()
    for node in ast.walk(ast.parse(Path(config.__file__).read_text())):
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and not target.id.startswith('_'):names.add(target.id)
    assert names=={f['key'] for f in SCHEMA}

@pytest.mark.parametrize('change',[
    {'pid_ki':0},{'kw_elements':float('nan')},{'kwh_rate':-1},{'listening_port':80},
    {'listening_port':1234.5},{'simulate':'false'},{'sensor_time_wait':1,'temperature_average_samples':100},
    {'max31855':True,'max31856':True},{'max31855':False,'max31856':False},
    {'thermocouple_type':'J'},{'gpio_heat':'PH5'},{'gpio_heat':'__import__("os")'},
    {'automatic_restart_state_file':'../../outside.json'},{'kiln_profiles_directory':'/etc'},
    {'automatic_restart_state_file':'settings.json'},{'log_format':'%(unknown)s'},
    {'emergency_shutoff_temp':2000},{'currency_type':'x\n'}, {'made_up':42}
])
def test_invalid_values_do_not_write_any_settings(settings,change):
    store,_=settings
    with pytest.raises(SettingsError):store.save(change,store.revision())
    assert not store.pending.exists() and not store.active.exists()

def test_save_is_staged_and_recovery_does_not_activate_it(settings):
    store,module=settings;original=copy.deepcopy(store.current)
    store.save({'kwh_rate':.7},store.revision())
    assert store.desired()['kwh_rate']==.7 and store.current==original
    fresh=dict(vars(module));load_overrides(fresh)
    assert fresh['kwh_rate']==original['kwh_rate']

def test_apply_persists_values_and_backup_without_editing_base(settings):
    store,module=settings
    store.save({'kw_elements':12,'currency_type':'₪'},store.revision())
    store.apply(store.revision())
    assert not store.pending.exists()
    fresh=dict(vars(module));load_overrides(fresh)
    assert fresh['kw_elements']==12 and module.kw_elements==11
    assert list((store.root/'storage/settings-backups').glob('*.json'))

def test_stale_revision_cannot_overwrite_another_editor(settings):
    store,_=settings;revision=store.revision();store.save({'kwh_rate':.7},revision)
    with pytest.raises(SettingsError):store.save({'kwh_rate':.8},revision)
    assert store.desired()['kwh_rate']==.7

def test_environment_overrides_remain_locked(settings,monkeypatch):
    store,module=settings;monkeypatch.setenv('KILN_SIMULATE','1')
    with pytest.raises(SettingsError):store.save({'simulate':False},store.revision())
    store.save({'kwh_rate':.7},store.revision());store.apply(store.revision())
    fresh=dict(vars(module));load_overrides(fresh)
    assert fresh['simulate'] is True

def test_storage_paths_copy_existing_data(settings):
    store,_=settings
    store.save({'kiln_profiles_directory':'storage/new-profiles','automatic_restart_state_file':'storage/recovery/state.json'},store.revision())
    store.apply(store.revision())
    assert json.loads((store.root/'storage/new-profiles/one.json').read_text())['temp_units']=='c'
    assert json.loads((store.root/'storage/recovery/state.json').read_text())['state']=='IDLE'

def test_symlink_cannot_escape_controller_directory(settings,tmp_path):
    store,_=settings;outside=tmp_path.parent/'settings-outside';outside.mkdir(exist_ok=True)
    (store.root/'storage/escape').symlink_to(outside,target_is_directory=True)
    with pytest.raises(SettingsError):store.save({'automatic_restart_state_file':'storage/escape/state.json'},store.revision())

def test_failed_atomic_save_keeps_previous_pending(settings,monkeypatch):
    store,_=settings;store.save({'kwh_rate':.7},store.revision());before=store.pending.read_bytes()
    monkeypatch.setattr('lib.settings_store.os.replace',lambda *args:(_ for _ in ()).throw(OSError('disk error')))
    with pytest.raises(OSError):store.save({'kwh_rate':.8},store.revision())
    assert store.pending.read_bytes()==before

def test_port_in_use_does_not_activate_settings(settings):
    store,_=settings
    with socket.socket() as sock:
        sock.bind(('0.0.0.0',0));sock.listen()
        store.save({'listening_port':sock.getsockname()[1]},store.revision())
        with pytest.raises(SettingsError):store.apply(store.revision())
    assert not store.active.exists() and store.pending.exists()

def test_integer_settings_are_normalized(settings):
    store,_=settings
    assert type(validate({'listening_port':8084.0},store.current,store.root)['listening_port']) is int

def test_recovery_cannot_be_saved_in_programs_directory(settings):
    store,_=settings
    with pytest.raises(SettingsError):store.save({'automatic_restart_state_file':'storage/profiles/state.json'},store.revision())

def request(app,path,method='GET',body=None,token=None,origin='http://kiln:8081'):
    payload=json.dumps(body or {}).encode();status=[]
    environ={'REQUEST_METHOD':method,'PATH_INFO':path,'SERVER_NAME':'kiln','SERVER_PORT':'8081','SERVER_PROTOCOL':'HTTP/1.1','HTTP_HOST':'kiln:8081','wsgi.url_scheme':'http','wsgi.input':io.BytesIO(payload),'wsgi.errors':io.StringIO(),'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(payload)),'HTTP_ORIGIN':origin}
    if token:environ['HTTP_X_KILN_SETTINGS']=token
    result=b''.join(app(environ,lambda s,h,*a:status.append(s)))
    try:result=json.loads(result)
    except ValueError:result=result.decode()
    return int(status[0].split()[0]),result

def test_api_blocks_cross_origin_and_active_firing_apply(settings,monkeypatch):
    store,module=settings;app=bottle.Bottle()
    oven=SimpleNamespace(state='RUNNING',_restart_lock=threading.RLock(),should_i_automatic_restart=lambda:False)
    install(app,module,oven)
    code,doc=request(app,'/api/settings');assert code==200 and not doc['can_apply']
    body={'revision':doc['revision'],'values':dict(doc['values'],kwh_rate=.7)}
    assert request(app,'/api/settings','POST',body)[0]==403
    assert request(app,'/api/settings','POST',body,doc['token'],'http://elsewhere')[0]==403
    code,saved=request(app,'/api/settings','POST',body,doc['token']);assert code==200
    assert request(app,'/api/settings/apply','POST',{'revision':saved['revision']},doc['token'])[0]==409
    assert not store.active.exists()

def test_api_idle_apply_schedules_restart_and_preserves_idle(settings,monkeypatch):
    store,module=settings;app=bottle.Bottle();calls=[]
    oven=SimpleNamespace(state='IDLE',_restart_lock=threading.RLock(),should_i_automatic_restart=lambda:False,save_state=lambda:calls.append('save'))
    monkeypatch.setattr('lib.settings_api.gevent.spawn_later',lambda delay,callback:calls.append('restart'))
    control=install(app,module,oven)
    _,doc=request(app,'/api/settings');body={'revision':doc['revision'],'values':dict(doc['values'],kwh_rate=.7)}
    _,saved=request(app,'/api/settings','POST',body,doc['token'])
    code,result=request(app,'/api/settings/apply','POST',{'revision':saved['revision']},doc['token'])
    assert code==200 and result['restarting'] and control['restarting']
    assert calls==['save','restart'] and oven.state=='IDLE'

def test_api_does_not_cancel_pending_firing_recovery(settings):
    store,module=settings;app=bottle.Bottle()
    oven=SimpleNamespace(state='IDLE',_restart_lock=threading.RLock(),should_i_automatic_restart=lambda:True)
    install(app,module,oven)
    _,doc=request(app,'/api/settings');assert not doc['can_apply']
    assert request(app,'/api/settings/apply','POST',{'revision':doc['revision']},doc['token'])[0]==409
