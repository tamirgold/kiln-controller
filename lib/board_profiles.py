"""Explicit header pin profiles; importing this module never opens GPIO.

The implicit Orange Pi profile retains the deployed fork's defaults. New
installations should set KILN_BOARD, including when running the simulator.
"""
from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import re


PIN_KEYS = ('spi_sclk', 'spi_miso', 'spi_mosi', 'spi_cs', 'gpio_heat')
THERMOCOUPLE_TYPES = ('B', 'E', 'J', 'K', 'N', 'R', 'S', 'T')


class BoardConfigurationError(ValueError):
    """Selected board, detected hardware or configured pins do not agree."""


def detected_model():
    for location in ('/proc/device-tree/model', '/sys/firmware/devicetree/base/model'):
        try:
            return Path(location).read_text().strip('\0\n ')
        except FileNotFoundError:
            pass
    return None


@dataclass(frozen=True)
class BoardProfile:
    name: str
    label: str
    header: dict
    defaults: dict

    def canonical_pin(self, value):
        if isinstance(value, str):
            name = value
            if self.name == 'raspberry-pi' and name.startswith('BCM'):
                name = 'D' + name[3:]
            if name in self.header:
                return name
        else:
            # Serialize existing Blinka pin objects without importing any of
            # their drivers. H616 ids are (gpiochip, offset); Pi ids are BCM.
            pin_id = getattr(value, 'id', None)
            for name in self.header:
                if self.name == 'raspberry-pi':
                    expected = int(name[1:])
                    if type(pin_id) is int and pin_id == expected:
                        return name
                elif isinstance(pin_id, tuple) and len(pin_id) == 2:
                    expected = (ord(name[1]) - ord('A')) * 32 + int(name[2:])
                    if pin_id[1] == expected:
                        return name
        raise BoardConfigurationError(
            f'GPIO {value!r} is not in the {self.label} header profile. '
            'Check KILN_BOARD and the saved wiring settings; pin names are not portable between boards.')

    def options(self):
        return {name: f'Pin {physical} · {name}' +
                (f' / BCM{name[1:]}' if self.name == 'raspberry-pi' else '')
                for name, physical in sorted(self.header.items(), key=lambda item: item[1])}

    def validate_model(self, model):
        if self.name == 'raspberry-pi':
            matches = model and re.fullmatch(
                r'Raspberry Pi (?:3 Model (?:B(?:\+| Plus)?|A(?:\+| Plus))|4 Model B)(?: Rev [\w.]+)?', model)
        else:
            # Device-tree capitalization and spacing differ between OS images.
            matches = model and re.sub(r'[^a-z0-9]', '', model.lower()) == 'orangepizero2w'
        if not matches:
            raise BoardConfigurationError(
                f'KILN_BOARD={self.name} does not match a supported detected board '
                f'({model or "no device-tree model found"}). '
                'Use the matching profile on supported hardware, or KILN_SIMULATE=1 for a desktop preview.')

    def load_pins(self):
        # Check the actual machine before forcing Blinka. This prevents a Pi
        # profile or legacy Orange profile from being used on the wrong board.
        self.validate_model(detected_model())
        if self.name == 'orange-pi-zero-2w':
            expected = {'BLINKA_FORCEBOARD': 'ORANGE_PI_ZERO_2', 'BLINKA_FORCECHIP': 'H616'}
            for key, value in expected.items():
                if key in os.environ and os.environ[key] != value:
                    raise BoardConfigurationError(f'{key} conflicts with KILN_BOARD={self.name}.')
            for key, value in expected.items():
                os.environ.setdefault(key, value)
            board = importlib.import_module('board')
            self.validate_blinka(board)
            # The shared H616 module exposes the complete Zero 2W header,
            # including pins missing from Blinka's Orange Pi Zero 2 board map.
            return importlib.import_module('adafruit_blinka.microcontroller.allwinner.h616.pin')
        if 'BLINKA_FORCEBOARD' in os.environ or 'BLINKA_FORCECHIP' in os.environ:
            raise BoardConfigurationError(
                'Unset BLINKA_FORCEBOARD and BLINKA_FORCECHIP for the raspberry-pi profile; '
                'Blinka must detect the real Raspberry Pi.')
        board = importlib.import_module('board')
        self.validate_blinka(board)
        return board

    def validate_blinka(self, board):
        identifier = getattr(board, 'board_id', None)
        allowed = ({'RASPBERRY_PI_3B', 'RASPBERRY_PI_3B_PLUS', 'RASPBERRY_PI_3A_PLUS', 'RASPBERRY_PI_4B'}
                   if self.name == 'raspberry-pi' else {'ORANGE_PI_ZERO_2'})
        if identifier not in allowed:
            raise BoardConfigurationError(
                f'Blinka detected {identifier!r}, which does not match KILN_BOARD={self.name}. '
                'Check installed hardware packages and Blinka environment overrides.')


_ORANGE_HEADER = {'PI8':3,'PI7':5,'PI13':7,'PH2':11,'PI1':12,'PH3':13,'PI5':15,
                 'PI14':16,'PH4':18,'PH7':19,'PH8':21,'PI6':22,'PH6':23,'PH5':24,
                 'PH9':26,'PI10':27,'PI9':28,'PI0':29,'PI15':31,'PI11':32,
                 'PI12':33,'PI2':35,'PC12':36,'PI16':37,'PI4':38,'PI3':40}
_PI_HEADER = {'D2':3,'D3':5,'D4':7,'D14':8,'D15':10,'D17':11,'D18':12,'D27':13,
              'D22':15,'D23':16,'D24':18,'D10':19,'D9':21,'D25':22,'D11':23,'D8':24,
              'D7':26,'D0':27,'D1':28,'D5':29,'D6':31,'D12':32,'D13':33,'D19':35,
              'D16':36,'D26':37,'D20':38,'D21':40}
PROFILES = {
    'orange-pi-zero-2w': BoardProfile('orange-pi-zero-2w', 'Orange Pi Zero 2W 40-pin',
        _ORANGE_HEADER, dict(zip(PIN_KEYS, ('PH6', 'PH8', 'PH7', 'PH5', 'PI16')))),
    'raspberry-pi': BoardProfile('raspberry-pi', 'Raspberry Pi 3 / 4 40-pin',
        _PI_HEADER, dict(zip(PIN_KEYS, ('D11', 'D9', 'D10', 'D8', 'D26')))),
}


def get_profile(name=None):
    if name is None:
        name = os.environ.get('KILN_BOARD', 'orange-pi-zero-2w')
    try:
        return PROFILES[name]
    except KeyError:
        raise BoardConfigurationError(
            f'Unknown KILN_BOARD={name!r}. Choose raspberry-pi or orange-pi-zero-2w.') from None


def namespace_profile(namespace):
    return namespace.get('_board_profile') or get_profile()


def thermocouple_name(value):
    if isinstance(value, str) and value in THERMOCOUPLE_TYPES:
        return value
    # MAX31856 ThermocoupleType values are the 0..7 register encodings. Retain
    # compatibility with older config.py files storing those enum constants.
    if type(value) is int and 0 <= value < len(THERMOCOUPLE_TYPES):
        return THERMOCOUPLE_TYPES[value]
    raise BoardConfigurationError(f'Unknown thermocouple type {value!r}.')


def initialize_hardware(namespace):
    """Resolve saved pin names only after overrides determine simulation mode."""
    if namespace['simulate']:
        return
    profile = namespace_profile(namespace)
    names = {key: profile.canonical_pin(namespace[key]) for key in PIN_KEYS}
    try:
        pins = profile.load_pins()
        resolved = {key: getattr(pins, name) for key, name in names.items()}
    except (ImportError, NotImplementedError, AttributeError) as exc:
        raise BoardConfigurationError(
            f'Cannot initialize {profile.label} GPIO: {exc}. '
            'Install the matching hardware dependencies or use KILN_SIMULATE=1.') from exc
    namespace.update(resolved)
