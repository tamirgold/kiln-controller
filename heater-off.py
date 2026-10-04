#!/usr/bin/env python3
"""Set the SSR driver signal LOW before startup and after process exit."""
import config
from digitalio import DigitalInOut
with DigitalInOut(config.gpio_heat) as heater:
    heater.switch_to_output(value=config.gpio_heat_invert)
