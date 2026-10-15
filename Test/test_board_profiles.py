"""Software profile checks; these do not qualify a board or a kiln electrically."""
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from types import SimpleNamespace

import pytest

from lib.board_profiles import (BoardConfigurationError, PIN_KEYS, PROFILES,
                                get_profile, initialize_hardware, thermocouple_name)


ROOT = Path(__file__).resolve().parents[1]
REJECT_HARDWARE = '''
import sys
class RejectHardware:
    def find_spec(self, fullname, path=None, target=None):
        roots = ('board', 'digitalio', 'busio', 'adafruit_blinka',
                 'adafruit_platformdetect', 'adafruit_bitbangio',
                 'adafruit_max31855', 'adafruit_max31856', 'RPi', 'gpiod')
        if fullname.split('.')[0] in roots:
            raise AssertionError('Hardware import attempted: ' + fullname)
sys.meta_path.insert(0, RejectHardware())
'''


def isolated_python(tmp_path, source, profile='raspberry-pi', simulate='1', saved=None):
    environment = dict(os.environ)
    for key in ('KILN_BOARD', 'KILN_SIMULATE', 'BLINKA_FORCEBOARD', 'BLINKA_FORCECHIP'):
        environment.pop(key, None)
    if profile is not None:
        environment['KILN_BOARD'] = profile
    if simulate is not None:
        environment['KILN_SIMULATE'] = simulate
    settings_path = tmp_path/'settings.json'
    environment['KILN_SETTINGS_FILE'] = str(settings_path)
    environment['KILN_STATE_FILE'] = str(tmp_path/'recovery.json')
    if saved is not None:
        settings_path.write_text(json.dumps({'version': 1, 'values': saved}))
    return subprocess.run([sys.executable, '-c', REJECT_HARDWARE + textwrap.dedent(source)],
                          cwd=ROOT, env=environment, text=True, capture_output=True, timeout=15)


@pytest.mark.parametrize('profile', PROFILES)
def test_simulator_settings_and_service_hook_never_import_gpio(tmp_path, profile):
    result = isolated_python(tmp_path, '''
        import json, runpy, threading
        import config
        from lib import oven
        from lib.settings_store import Store
        from lib.hardware import heater_off
        threading.Thread.start = lambda self: None
        oven.time.sleep = lambda seconds: None
        kiln = oven.SimulatedOven()
        kiln.run_profile(oven.Profile(json.dumps({
            'name': 'software test', 'data': [[0, 20], [3600, 200]], 'temp_units': 'c'
        })), allow_seek=False)
        kiln.target = 100
        kiln.heat_then_cool()
        assert kiln.temperature > config.sim_t_env
        assert kiln.get_state()['energy_accounting']['heater_on_seconds'] > 0
        store = Store(config)
        store.save({'kwh_rate': .8}, store.revision())
        store.apply(store.revision())
        assert store.active.exists()
        assert store.current['thermocouple_type'] == 'K'
        output = oven.Output()
        output.heat(0)
        assert output.heater.value == config.gpio_heat_invert
        heater_off(config)
        runpy.run_path('heater-off.py', run_name='__main__')
        print('simulation and settings exercised with all hardware imports forbidden')
    ''', profile=profile)
    assert result.returncode == 0, result.stdout + result.stderr


def test_saved_simulation_is_read_before_any_hardware_import(tmp_path):
    result = isolated_python(tmp_path, '''
        import config
        from lib.oven import SimulatedBoard
        assert config.simulate is True
        assert config.sensor_time_wait == 4
        assert config.gpio_heat_invert is True
        assert config.gpio_heat == 'PI2'
        assert config.automatic_restarts is False
        SimulatedBoard()
    ''', profile=None, simulate=None,
        saved={'simulate': True, 'sensor_time_wait': 4, 'gpio_heat_invert': True,
               'gpio_heat': 'PI2', 'automatic_restarts': False})
    assert result.returncode == 0, result.stdout + result.stderr


def test_simulation_environment_overrides_saved_real_mode(tmp_path):
    result = isolated_python(tmp_path, '''
        import config
        assert config.simulate is True
    ''', saved={'simulate': False})
    assert result.returncode == 0, result.stdout + result.stderr


def test_real_environment_override_does_not_bypass_model_check(tmp_path):
    result = isolated_python(tmp_path, '''
        from lib import board_profiles
        board_profiles.detected_model = lambda: 'Orange Pi Zero 2W'
        import config
    ''', simulate='0', saved={'simulate': True})
    assert result.returncode != 0
    assert 'does not match a supported detected board' in result.stderr
    assert 'Hardware import attempted' not in result.stderr


def test_saved_other_board_pins_fail_with_actionable_startup_error(tmp_path):
    result = isolated_python(tmp_path, 'import config', saved={'gpio_heat': 'PI16'})
    assert result.returncode != 0
    assert 'Cannot load settings from' in result.stderr
    assert 'gpio_heat:' in result.stderr
    assert 'Raspberry Pi 3 / 4' in result.stderr
    assert 'Hardware import attempted' not in result.stderr


@pytest.mark.parametrize('profile,expected', [
    ('raspberry-pi', {'spi_sclk': ('D11', 23), 'spi_miso': ('D9', 21),
                    'spi_mosi': ('D10', 19), 'spi_cs': ('D8', 24), 'gpio_heat': ('D26', 37)}),
    ('orange-pi-zero-2w', {'spi_sclk': ('PH6', 23), 'spi_miso': ('PH8', 21),
                         'spi_mosi': ('PH7', 19), 'spi_cs': ('PH5', 24), 'gpio_heat': ('PI16', 37)}),
])
def test_default_wiring_is_explicit_and_complete(profile, expected):
    selected = get_profile(profile)
    assert {key: (name, selected.header[name]) for key, name in selected.defaults.items()} == expected
    assert len(set(selected.header.values())) == len(selected.header)


@pytest.mark.parametrize('model', [
    'Raspberry Pi 3 Model B Rev 1.2', 'Raspberry Pi 3 Model B Plus Rev 1.3',
    'Raspberry Pi 3 Model A Plus Rev 1.0', 'Raspberry Pi 4 Model B Rev 1.5',
])
def test_supported_pi_model_names(model):
    get_profile('raspberry-pi').validate_model(model)


@pytest.mark.parametrize('model', [
    None, 'Orange Pi Zero 2W', 'Raspberry Pi 5 Model B Rev 1.0',
    'Raspberry Pi 400 Rev 1.0', 'Raspberry Pi Compute Module 4 Rev 1.1',
    'Raspberry Pi Zero 2 W Rev 1.0', 'Raspberry Pi 2 Model B Rev 1.1',
])
def test_other_pi_models_and_mismatches_fail_before_imports(model, monkeypatch):
    from lib import board_profiles
    monkeypatch.setattr(board_profiles, 'detected_model', lambda: model)
    monkeypatch.setattr(board_profiles.importlib, 'import_module',
                        lambda name: pytest.fail('Imported hardware on an incompatible model: ' + name))
    with pytest.raises(BoardConfigurationError, match='does not match'):
        get_profile('raspberry-pi').load_pins()


def test_unknown_profile_is_rejected_even_in_simulation(tmp_path):
    result = isolated_python(tmp_path, 'import config', profile='banana-pi')
    assert result.returncode != 0
    assert 'Unknown KILN_BOARD' in result.stderr
    assert 'Hardware import attempted' not in result.stderr


@pytest.fixture
def profile_store(tmp_path, monkeypatch):
    import config
    from lib.settings_store import Store
    monkeypatch.setenv('KILN_SETTINGS_FILE', str(tmp_path/'settings.json'))
    monkeypatch.setenv('KILN_SIMULATE', '1')
    def make(profile):
        selected = get_profile(profile)
        values = dict(vars(config), __file__=str(tmp_path/'config.py'), _board_profile=selected,
                      simulate=True, automatic_restart_state_file=str(tmp_path/'state.json'),
                      kiln_profiles_directory=str(tmp_path/'storage/profiles'))
        values.update(selected.defaults)
        return Store(SimpleNamespace(**values))
    return make


@pytest.mark.parametrize('profile,pin', [('raspberry-pi', 'D25'), ('orange-pi-zero-2w', 'PI2')])
def test_settings_profile_roundtrip_preserves_wiring_and_controls(profile_store, profile, pin):
    from lib.settings_store import load_overrides, serialize
    store = profile_store(profile)
    changes = {'gpio_heat': pin, 'gpio_heat_invert': True, 'sensor_time_wait': 4,
               'automatic_restarts': False, 'max31855': False, 'max31856': True,
               'thermocouple_type': 'S'}
    store.save(changes, store.revision())
    store.apply(store.revision())
    fresh = dict(vars(store.config))
    load_overrides(fresh)
    roundtrip = serialize(fresh, store.root)
    for key, value in changes.items():
        assert roundtrip[key] == value
    assert next(item for item in store.schema() if item['key'] == 'gpio_heat')['options'] == store.profile.options()


def test_pi_aliases_normalize_and_cannot_hide_duplicate_gpio(profile_store):
    from lib.settings_store import SettingsError, validate
    store = profile_store('raspberry-pi')
    normalized = validate({'gpio_heat': 'BCM25'}, store.current, store.root, profile=store.profile)
    assert normalized['gpio_heat'] == 'D25'
    with pytest.raises(SettingsError, match='Check the highlighted settings'):
        validate({'gpio_heat': 'BCM8'}, store.current, store.root, profile=store.profile)
    with pytest.raises(SettingsError):
        validate({'gpio_heat': 'PI16'}, store.current, store.root, profile=store.profile)


@pytest.mark.parametrize('profile', PROFILES)
def test_blinka_pin_objects_serialize_without_importing_drivers(profile):
    selected = get_profile(profile)
    for name in selected.header:
        if profile == 'raspberry-pi':
            identifier = int(name[1:])
        else:
            identifier = (1, (ord(name[1]) - ord('A')) * 32 + int(name[2:]))
        assert selected.canonical_pin(SimpleNamespace(id=identifier)) == name


def test_legacy_thermocouple_enum_values_need_no_driver():
    assert [thermocouple_name(value) for value in range(8)] == ['B', 'E', 'J', 'K', 'N', 'R', 'S', 'T']
    assert thermocouple_name('K') == 'K'
    with pytest.raises(BoardConfigurationError):
        thermocouple_name(True)


@pytest.mark.parametrize('profile,model', [
    ('raspberry-pi', 'Raspberry Pi 4 Model B Rev 1.4'),
    ('orange-pi-zero-2w', 'OrangePi Zero2W'),
])
def test_real_profile_hydrates_only_after_model_check(profile, model, monkeypatch):
    from lib import board_profiles
    selected = get_profile(profile)
    for name in ('BLINKA_FORCEBOARD', 'BLINKA_FORCECHIP'):
        monkeypatch.delenv(name, raising=False)
    pins = SimpleNamespace(board_id='RASPBERRY_PI_4B' if profile == 'raspberry-pi' else 'ORANGE_PI_ZERO_2',
                           **{name: object() for name in selected.header})
    imports = []
    def fake_import(name):
        imports.append(name)
        if profile == 'raspberry-pi':
            assert 'BLINKA_FORCEBOARD' not in os.environ
        else:
            assert os.environ['BLINKA_FORCEBOARD'] == 'ORANGE_PI_ZERO_2'
            assert os.environ['BLINKA_FORCECHIP'] == 'H616'
        return pins
    monkeypatch.setattr(board_profiles, 'detected_model', lambda: model)
    monkeypatch.setattr(board_profiles.importlib, 'import_module', fake_import)
    namespace = dict(selected.defaults, simulate=False, _board_profile=selected)
    initialize_hardware(namespace)
    assert imports[0] == 'board'
    for key in PIN_KEYS:
        assert namespace[key] is getattr(pins, selected.defaults[key])
    # setdefault above changes the process environment; remove only our forced
    # values here so another test is not mistaken for an Orange Pi service.
    for name in ('BLINKA_FORCEBOARD', 'BLINKA_FORCECHIP'):
        monkeypatch.delenv(name, raising=False)


def test_blinka_mismatch_is_rejected_despite_matching_device_tree(monkeypatch):
    from lib import board_profiles
    for name in ('BLINKA_FORCEBOARD', 'BLINKA_FORCECHIP'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(board_profiles, 'detected_model', lambda: 'Raspberry Pi 4 Model B Rev 1.4')
    monkeypatch.setattr(board_profiles.importlib, 'import_module',
                        lambda name: SimpleNamespace(board_id='RASPBERRY_PI_5'))
    with pytest.raises(BoardConfigurationError, match='Blinka detected'):
        get_profile('raspberry-pi').load_pins()


@pytest.mark.parametrize('invert', [False, True])
def test_service_off_hook_honors_installed_driver_polarity(invert, monkeypatch):
    from lib import hardware
    writes = []
    class FakeOutput:
        def __init__(self, pin):
            assert pin == 'configured pin'
        def __enter__(self): return self
        def __exit__(self, *args): writes.append('closed')
        def switch_to_output(self, value): writes.append(value)
    monkeypatch.setattr(hardware.importlib, 'import_module',
                        lambda name: SimpleNamespace(DigitalInOut=FakeOutput))
    hardware.heater_off(SimpleNamespace(simulate=False, gpio_heat='configured pin', gpio_heat_invert=invert))
    assert writes == [invert, 'closed']


def test_service_off_simulation_skips_even_output_creation(monkeypatch):
    from lib import hardware
    monkeypatch.setattr(hardware, 'DigitalIO', lambda *args: pytest.fail('GPIO adapter was opened'))
    hardware.heater_off(SimpleNamespace(simulate=True))
