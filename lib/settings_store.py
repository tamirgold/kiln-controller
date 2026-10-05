"""Validated, staged configuration. JSON contains data only, never Python code."""
import copy
import hashlib
import json
import logging
import math
import os
import socket
from pathlib import Path
import tempfile
import time

PIN_HEADER={'PI8':3,'PI7':5,'PI13':7,'PH2':11,'PI1':12,'PH3':13,'PI5':15,'PI14':16,'PH4':18,'PH7':19,'PH8':21,'PI6':22,'PH6':23,'PH5':24,'PH9':26,'PI10':27,'PI9':28,'PI0':29,'PI15':31,'PI11':32,'PI12':33,'PI2':35,'PC12':36,'PI16':37,'PI4':38,'PI3':40}
GROUPS=[('general','Electricity & display'),('firing','Firing behavior'),('pid','PID control'),('sensor','Sensor & wiring'),('recovery','Power-loss recovery'),('protection','Protection overrides'),('system','Server & storage'),('simulation','Simulation'),('legacy','Compatibility')]
SCHEMA=[]
def field(key,label,group,kind='number',help='',minimum=None,maximum=None,options=None,readonly=None):
    d=dict(key=key,label=label,group=group,type=kind,help=help)
    if minimum is not None:d['min']=minimum
    if maximum is not None:d['max']=maximum
    if options is not None:d['options']=options
    if readonly:d['readonly']=readonly
    SCHEMA.append(d)

field('kw_elements','Installed heating power','general',help='Total rated power of the elements, in kW.',minimum=.001,maximum=1000)
field('kwh_rate','Electricity tariff','general',help='Price per kWh. Used with heater on-time to estimate cost.',minimum=0,maximum=10000)
field('currency_type','Currency symbol','general','string',help='For example ₪, €, $, or ILS. Maximum 8 characters.')
field('temp_scale','Temperature units','general','select',help='Changing units converts temperature limits, offsets and PID gains. Saved programs are converted when loaded.',options={'c':'Celsius (°C)','f':'Fahrenheit (°F)'})
field('time_scale_profile','Schedule editor time units','general','select',options={'s':'Seconds','m':'Minutes','h':'Hours'})
field('time_scale_slope','Heating / cooling rate units','general','select',options={'s':'Degrees per second','m':'Degrees per minute','h':'Degrees per hour'})
field('seek_start','Skip initial schedule when kiln is warm','firing','boolean',help='A new firing can start at the matching temperature in its schedule.')
field('kiln_must_catch_up','Wait for temperature before advancing','firing','boolean',help='Waits when too cold on heating ramps, too hot on cooling ramps, or outside the catch-up tolerance during holds. PID still controls heating when the program advances.')
field('catch_up_tolerance','Catch-up temperature tolerance','firing',help='Temperature difference allowed before the schedule waits. Zero uses the PID control window. A positive value keeps temperature waits independent of PID tuning.',minimum=0,maximum=1000)
field('sensor_time_wait','Control cycle (seconds)','firing',help='One complete heater on/off cycle. Shorter cycles switch the relay more often. Choose a cycle suitable for the installed relay.',minimum=.5,maximum=30)
field('throttle_below_temp','Low-temperature throttle threshold','firing',help='Temperature below which the warm-up output limit applies.',minimum=-100,maximum=3500)
field('throttle_percent','Low-temperature output limit (%)','firing',help='100 allows full power. Applies below the throttle threshold when outside the PID window.',minimum=1,maximum=100)
field('pid_kp','Proportional gain (Kp)','pid',help='Response to the current temperature error.',minimum=0,maximum=100000)
field('pid_ki','Integral parameter (Ki)','pid',help='This controller uses inverse Ki: smaller values give stronger integral action. Must be greater than zero.',minimum=.000001,maximum=10000000)
field('pid_kd','Derivative gain (Kd)','pid',help='Response to changes in temperature error.',minimum=0,maximum=10000000)
field('pid_control_window','PID control window','pid',help='Temperature difference around the target. Outside this window the controller requests maximum heating or no heating.',minimum=.001,maximum=1000)
field('thermocouple_offset','Temperature calibration offset','sensor',help='Added to the sensor reading, in the selected temperature units.',minimum=-200,maximum=200)
field('temperature_average_samples','Samples per control cycle','sensor','integer',help='The median of these readings is used. Sampling interval must be at least 0.1 seconds.',minimum=1,maximum=100)
field('max31855','Use MAX31855','sensor','boolean',help='Select exactly one thermocouple converter. MAX31855 uses a type K thermocouple.')
field('max31856','Use MAX31856','sensor','boolean',help='Requires a MAX31856 board and MOSI wiring.')
field('thermocouple_type','Thermocouple type','sensor','select',help='MAX31856 types; keep K when using MAX31855.',options={v:'Type '+v for v in ['B','E','J','K','N','R','S','T']})
field('ac_freq_50hz','50 Hz noise filtering','sensor','boolean',help='MAX31856 only: enable for 50 Hz mains (Israel). MAX31855 has no configurable mains filter.')
for k,label in [('spi_sclk','Thermocouple clock (CLK)'),('spi_miso','Thermocouple data out (DO / MISO)'),('spi_mosi','Thermocouple data in (MOSI)'),('spi_cs','Thermocouple chip select (CS)'),('gpio_heat','SSR control output')]:
    field(k,label,'sensor','select',help='Orange Pi 40-pin header. Wiring must match. Leave MOSI physically unconnected with MAX31855.',options={k:f'Pin {p} · {k}' for k,p in sorted(PIN_HEADER.items(),key=lambda x:x[1])})
field('gpio_heat_invert','Invert SSR control signal','sensor','boolean',help='Enable only for an active-low driver. An incorrect polarity can turn the heater on when it should be off.')
field('automatic_restarts','Automatic recovery after power loss','recovery','boolean')
field('automatic_restart_window','Maximum recovery delay (minutes)','recovery',help='Resume only when the saved firing state is younger than this.',minimum=.1,maximum=1440)
field('require_synced_clock_for_restart','Require a synchronized clock','recovery','boolean',help='Verifies outage duration with Chrony before restoring a firing.')
field('emergency_shutoff_temp','Over-temperature shutoff','protection',help='Heating stops at or above this temperature unless the override below is enabled. Never exceed the kiln or thermocouple rating.',minimum=1,maximum=3500)
for k,label in [('ignore_temp_too_high','Ignore over-temperature shutoff'),('ignore_tc_lost_connection','Ignore disconnected thermocouple errors'),('ignore_tc_cold_junction_range_error','Ignore cold-junction range faults'),('ignore_tc_range_error','Ignore thermocouple range faults'),('ignore_tc_cold_junction_temp_high','Ignore high cold-junction temperature'),('ignore_tc_cold_junction_temp_low','Ignore low cold-junction temperature'),('ignore_tc_temp_high','Ignore high thermocouple temperature'),('ignore_tc_temp_low','Ignore low thermocouple temperature'),('ignore_tc_voltage_error','Ignore sensor voltage faults'),('ignore_tc_short_errors','Ignore thermocouple short-circuit faults'),('ignore_tc_unknown_error','Ignore unknown sensor errors'),('ignore_tc_too_many_errors','Ignore repeated sensor errors')]:
    field(k,label,'protection','boolean',help='Enabling this bypasses the named protection. Fresh, valid sensor readings are still required for heating.')
field('listening_port','Web server port','system','integer',help='Applying a port change moves the dashboard to the new port.',minimum=1024,maximum=65535)
field('log_level','Logging detail','system','select',options={'DEBUG':'Debug','INFO':'Information','WARNING':'Warnings','ERROR':'Errors','CRITICAL':'Critical only'})
field('log_format','Log message format','system','string',help='Python logging format. Only valid logging placeholders are accepted.')
field('automatic_restart_state_file','Recovery state file','system','path',help='state.json or a .json file under storage/. The last state is copied when this path changes.')
field('kiln_profiles_directory','Program storage directory','system','path',help='A directory under storage/. Existing programs are copied when changing to an empty directory.')
field('simulate','Simulation mode','simulation','boolean',help='Runs a virtual kiln. Hardware heating is disabled.')
field('sim_t_env','Simulated ambient temperature','simulation',minimum=-100,maximum=3500)
for k,label in [('sim_c_heat','Element heat capacity (J/K)'),('sim_c_oven','Kiln heat capacity (J/K)'),('sim_p_heat','Simulated heater power (W)'),('sim_R_o_nocool','Kiln-to-air thermal resistance (K/W)'),('sim_R_ho_noair','Element-to-kiln thermal resistance (K/W)')]:
    field(k,label,'simulation',minimum=.000001,maximum=10000000)
field('sim_speedup_factor','Simulation speed multiplier','simulation',minimum=.1,maximum=1000)
for k,label in [('sim_R_o_cool','Cooling thermal resistance'),('sim_R_ho_air','Forced-air thermal resistance')]:
    field(k,label,'legacy',readonly='Unused by the current simulator.')
field('stop_integral_windup','Legacy integral windup flag','legacy','boolean',readonly='Deprecated. Integral windup protection is automatic.')
INDEX={f['key']:f for f in SCHEMA}
ENV_KEYS={'simulate':'KILN_SIMULATE','listening_port':'KILN_PORT','automatic_restart_state_file':'KILN_STATE_FILE'}
ABS_TEMP=['emergency_shutoff_temp','throttle_below_temp','sim_t_env']
DELTA_TEMP=['thermocouple_offset','pid_control_window','catch_up_tolerance']

class SettingsError(ValueError):
    def __init__(self,message,errors=None):super().__init__(message);self.errors=errors or {}

def pin_module():
    from adafruit_blinka.microcontroller.allwinner.h616 import pin
    return pin

def serialize(namespace,root):
    result={}
    pins=None
    for f in SCHEMA:
        k=f['key'];v=namespace[k]
        if k in ('spi_sclk','spi_mosi','spi_miso','spi_cs','gpio_heat'):
            pins=pins or pin_module()
            v=next((name for name in PIN_HEADER if getattr(pins,name).id==v.id),None)
            if v is None:raise SettingsError('Unrecognized GPIO assignment: '+k)
        elif k=='thermocouple_type':
            import adafruit_max31856
            v=next(name for name in INDEX[k]['options'] if getattr(adafruit_max31856.ThermocoupleType,name)==v)
        elif k=='log_level':v=logging.getLevelName(v)
        elif f['type']=='boolean':v=bool(v)
        elif f['type']=='path':
            try:v=str(Path(v).relative_to(root))
            except ValueError:v=str(v)
        result[k]=v
    return result

def contained_path(root,value,key):
    p=Path(value)
    if not p.is_absolute():p=root/p
    resolved=p.resolve()
    try:relative=resolved.relative_to(root.resolve())
    except ValueError:raise SettingsError('Paths must remain inside the controller directory.',{key:'Use a path under storage/.'})
    if (key=='automatic_restart_state_file' and relative==Path('state.json')):return resolved
    if not relative.parts or relative.parts[0]!='storage' or len(relative.parts)<2:
        raise SettingsError('Use a path under storage/.',{key:'Use a subdirectory or file under storage/.'})
    if relative.parts[1] in ('settings-backups','firings','simulated-firings'):raise SettingsError('Controller records use this directory.',{key:'Choose a different storage path.'})
    if key=='automatic_restart_state_file' and resolved.suffix!='.json':raise SettingsError('State files must end in .json.',{key:'Use a .json file.'})
    return resolved

def validate(values,base,root,environment=None):
    if not isinstance(values,dict):raise SettingsError('Settings must be an object.')
    unknown=set(values)-set(INDEX)
    if unknown:raise SettingsError('Unknown settings: '+', '.join(sorted(unknown)))
    result=copy.deepcopy(base);result.update(values);errors={};environment=environment or {}
    for k,f in INDEX.items():
        v=result.get(k);kind=f['type']
        if k not in result:errors[k]='Missing value.';continue
        locked=f.get('readonly') or (k in ENV_KEYS and ENV_KEYS[k] in environment)
        if locked and v!=base[k]:errors[k]='This value is managed by the running service.'
        if kind=='boolean' and type(v) is not bool:errors[k]='Choose on or off.'
        elif kind in ('number','integer'):
            if type(v) not in (int,float) or not math.isfinite(v):errors[k]='Enter a finite number.'
            elif kind=='integer' and int(v)!=v:errors[k]='Enter a whole number.'
            elif ('min'in f and v<f['min']) or ('max'in f and v>f['max']):errors[k]=f"Use a value from {f.get('min')} to {f.get('max')}."
            elif kind=='integer':result[k]=int(v)
        elif kind=='select' and (not isinstance(v,str) or v not in f['options']):errors[k]='Choose one of the listed values.'
        elif kind in ('string','path'):
            if not isinstance(v,str) or not v.strip() or any(ord(c)<32 for c in v):errors[k]='Enter text without control characters.'
            elif len(v)>(8 if k=='currency_type' else 250):errors[k]='Value is too long.'
    if errors:raise SettingsError('Check the highlighted settings.',errors)
    if result['max31855']==result['max31856']:errors['max31855']=errors['max31856']='Select exactly one converter.'
    if result['max31855'] and result['thermocouple_type']!='K':errors['thermocouple_type']='MAX31855 requires type K.'
    pins=[result[k] for k in ['spi_sclk','spi_mosi','spi_miso','spi_cs','gpio_heat']]
    if len(set(pins))!=len(pins):errors['gpio_heat']='All five GPIO assignments must be different.'
    if result['sensor_time_wait']/result['temperature_average_samples']<.1-1e-9:errors['temperature_average_samples']='Allow at least 0.1 seconds per sensor sample.'
    limit_c=result['emergency_shutoff_temp'] if result['temp_scale']=='c' else (result['emergency_shutoff_temp']-32)/1.8
    maximum={'B':1820,'E':1000,'J':1200,'K':1372,'N':1300,'R':1768,'S':1768,'T':400}[result['thermocouple_type']]
    if not 0<limit_c<=maximum:errors['emergency_shutoff_temp']=f'Choose a limit above 0°C and no higher than the sensor range ({maximum}°C).'
    try:logging.Formatter(result['log_format']).format(logging.LogRecord('kiln',20,'file',1,'Check',(),None))
    except (ValueError,KeyError,TypeError):errors['log_format']='Invalid logging format.'
    for k in ('automatic_restart_state_file','kiln_profiles_directory'):
        # Service-enforced paths may be outside the editable storage area.
        if k not in ENV_KEYS or ENV_KEYS[k] not in environment:
            try:contained_path(root,result[k],k)
            except SettingsError as e:errors.update(e.errors)
    if not errors:
        state=(root/result['automatic_restart_state_file']).resolve()
        profiles=(root/result['kiln_profiles_directory']).resolve()
        if state.is_relative_to(profiles):errors['automatic_restart_state_file']='Keep recovery state outside the program directory.'
    if errors:raise SettingsError('Check the highlighted settings.',errors)
    return result

def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.settings-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf8') as f:
            json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(name):os.unlink(name)

def paths(root):
    active=Path(os.environ.get('KILN_SETTINGS_FILE',str(root/'settings.json')))
    return active,active.with_name(active.stem+'.pending.json')

def load_overrides(namespace):
    root=Path(namespace['__file__']).resolve().parent
    base=serialize(namespace,root)
    namespace['_settings_base_values']=base
    active,_=paths(root)
    if not active.exists():return
    document=json.loads(active.read_text())
    if document.get('version')!=1:raise SettingsError('Unsupported settings file version.')
    values=dict(document['values'])
    for key,env in ENV_KEYS.items():
        if env in os.environ:values[key]=base[key]
    values=validate(values,base,root,os.environ)
    for k,v in values.items():
        if k in ('spi_sclk','spi_mosi','spi_miso','spi_cs','gpio_heat'):v=getattr(pin_module(),v)
        elif k=='thermocouple_type':
            import adafruit_max31856
            v=getattr(adafruit_max31856.ThermocoupleType,v)
        elif k=='log_level':v=getattr(logging,v)
        elif INDEX[k]['type']=='path':v=str((root/v).resolve())
        namespace[k]=v

class Store:
    def __init__(self,config):
        self.config=config;self.root=Path(config.__file__).resolve().parent
        self.active,self.pending=paths(self.root)
        self.current=serialize(vars(config),self.root)
    def revision(self):
        raw=b''.join(p.read_bytes() if p.exists() else b'-' for p in (self.active,self.pending))
        return hashlib.sha256(raw+json.dumps(self.current,sort_keys=True).encode()).hexdigest()
    def desired(self):
        # New fields inherit their current defaults when an older pending
        # document predates them, just as active settings do during loading.
        values=dict(self.current)
        if self.pending.exists():
            pending=json.loads(self.pending.read_text())['values'];values.update(pending)
            if 'catch_up_tolerance' not in pending and values['temp_scale']!=self.current['temp_scale']:
                values['catch_up_tolerance']*=1.8 if values['temp_scale']=='f' else 1/1.8
        return values
    def schema(self):
        fields=copy.deepcopy(SCHEMA)
        for f in fields:
            if f['key'] in ENV_KEYS and ENV_KEYS[f['key']] in os.environ:f['readonly']='Set by service environment: '+ENV_KEYS[f['key']]
        return fields
    def check_revision(self,revision):
        if revision!=self.revision():raise SettingsError('Settings changed in another session. Reload before saving.',{'_conflict':True})
    def save(self,values,revision):
        self.check_revision(revision)
        validated=validate(values,self.current,self.root,os.environ)
        if validated==self.current:
            if self.pending.exists():self.pending.unlink()
        else:atomic_json(self.pending,dict(version=1,values=validated,saved_at=time.time()))
    def discard(self,revision):
        self.check_revision(revision)
        if self.pending.exists():self.pending.unlink()
    def apply(self,revision):
        self.check_revision(revision)
        if not self.pending.exists():raise SettingsError('There are no saved changes to apply.')
        values=validate(self.desired(),self.current,self.root,os.environ)
        if values['listening_port']!=self.current['listening_port']:
            try:
                with socket.socket() as sock:sock.bind(('0.0.0.0',values['listening_port']))
            except OSError:raise SettingsError('The selected port is unavailable.',{'listening_port':'Choose a port that is not in use.'})
        # Validate all destinations before copying. Identical copies from an
        # interrupted attempt are safe to reuse; existing different data is not.
        for k in ('automatic_restart_state_file','kiln_profiles_directory'):
            if values[k]==self.current[k]:continue
            source=contained_path(self.root,self.current[k],k);dest=contained_path(self.root,values[k],k)
            if dest.exists():
                if k=='kiln_profiles_directory':
                    if not dest.is_dir() or any(not p.is_file() or not (source/p.name).is_file() or p.read_bytes()!=(source/p.name).read_bytes() for p in dest.iterdir()):
                        raise SettingsError('Choose an empty destination for program storage.',{k:'Directory contains different data.'})
                elif not source.exists() or json.loads(dest.read_text())!=json.loads(source.read_text()):
                    raise SettingsError('Recovery destination already contains different data.',{k:'Choose a new file.'})
        for k in ('automatic_restart_state_file','kiln_profiles_directory'):
            if values[k]==self.current[k]:continue
            source=contained_path(self.root,self.current[k],k);dest=contained_path(self.root,values[k],k)
            if k=='kiln_profiles_directory':
                dest.mkdir(parents=True,exist_ok=True)
                for p in source.glob('*.json'):atomic_json(dest/p.name,json.loads(p.read_text()))
            elif source.exists():
                atomic_json(dest,json.loads(source.read_text()))
        backups=self.root/'storage'/'settings-backups';backups.mkdir(parents=True,exist_ok=True)
        atomic_json(backups/(str(time.time_ns())+'.json'),dict(version=1,values=self.current))
        atomic_json(self.active,dict(version=1,values=values,applied_at=time.time()))
        self.pending.unlink()
        return values
