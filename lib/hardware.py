"""Lazy GPIO boundary so desktop simulation needs only application packages."""
import importlib


class SimulatedDigitalInOut:
    """In-memory output; never touches a GPIO device or imports its driver."""
    def __init__(self, pin):
        self.pin = pin
        self.value = False

    def switch_to_output(self, value=False):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class DigitalIO:
    def __init__(self, config):
        self.config = config

    def DigitalInOut(self, pin):
        if self.config.simulate:
            return SimulatedDigitalInOut(pin)
        return importlib.import_module('digitalio').DigitalInOut(pin)


def heater_off(config):
    """Service lifecycle hook: respect polarity and do nothing in simulation."""
    if config.simulate:
        return
    with DigitalIO(config).DigitalInOut(config.gpio_heat) as heater:
        heater.switch_to_output(value=config.gpio_heat_invert)
