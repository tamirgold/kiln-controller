#!/usr/bin/env python3
"""Create safe first-install settings without replacing any existing file."""
import argparse
import json
import os
from pathlib import Path


def initialize(path):
    """Atomically create only a missing settings file; never follow a symlink."""
    defaults = {"version": 1, "values": {
        "simulate": True,
        "automatic_restarts": False,
        "sensor_time_wait": 30,
    }}
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(f"Preserved existing settings: {path}")
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(defaults, output, indent=2)
        output.write("\n")
    print(f"Created simulation-only first-install settings: {path}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path(os.environ.get(
        "KILN_SETTINGS_FILE", str(Path(__file__).resolve().parents[1] / "settings.json"))))
    arguments = parser.parse_args()
    initialize(arguments.path)
