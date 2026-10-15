#!/usr/bin/env python3
"""Set the configured SSR driver OFF; simulation never opens a GPIO line."""
import config
from lib.hardware import heater_off

heater_off(config)
