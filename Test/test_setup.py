"""Installation boundaries: no unexpected GPIO dependencies, mutation, or startup."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("board,requirement", [
    ("simulation", "requirements.txt"),
    ("raspberry-pi", "requirements-raspberry-pi.txt"),
    ("orange-pi-zero-2w", "requirements-hardware.txt"),
])
def test_dry_run_selects_dependencies_without_mutating(tmp_path, board, requirement):
    # Execute an isolated copy: a preview must not create any settings or venv.
    setup = tmp_path / "setup.sh"
    setup.write_text((ROOT / "setup.sh").read_text())
    result = subprocess.run(["bash", str(setup), "--board", board, "--dry-run"],
                            text=True, capture_output=True, check=True)
    assert f"pip install -r {requirement}" in result.stdout
    assert set(tmp_path.iterdir()) == {setup}
    assert "enable --now kiln-controller" not in result.stdout
    if board == "simulation":
        assert "libgpiod" not in result.stdout
        assert "system-site-packages" not in result.stdout


def test_safe_settings_created_once_and_existing_bytes_preserved(tmp_path):
    initialize = load_script("initialize-settings").initialize
    settings = tmp_path / "settings.json"
    assert initialize(settings)
    values = json.loads(settings.read_text())["values"]
    assert values["simulate"] is True
    assert values["automatic_restarts"] is False
    assert values["sensor_time_wait"] == 30
    assert "gpio_heat_invert" not in values  # Never guess a driver's polarity.
    settings.write_bytes(b'{"existing": "settings, including unknown fields"}\n')
    original = settings.read_bytes()
    assert initialize(settings) is False
    assert settings.read_bytes() == original


def test_settings_symlink_is_never_replaced_or_followed(tmp_path):
    initialize = load_script("initialize-settings").initialize
    destination = tmp_path / "existing.json"
    destination.write_text("keep me")
    settings = tmp_path / "settings.json"
    settings.symlink_to(destination)
    assert initialize(settings) is False
    assert settings.is_symlink()
    assert destination.read_text() == "keep me"


def test_simulation_service_cannot_touch_gpio_and_uses_custom_paths():
    service = load_script("create-service").render_service(
        "/home/maker/kiln controller", "maker", "raspberry-pi", "simulation")
    assert 'WorkingDirectory=/home/maker/kiln controller' in service
    assert '"/home/maker/kiln controller/venv/bin/python"' in service
    assert "Environment=KILN_SIMULATE=1" in service
    assert "storage/preview/raspberry-pi/state.json" in service
    assert "storage/preview/raspberry-pi/settings.json" in service
    assert "heater-off.py" not in service
    assert "SupplementaryGroups=gpio" not in service
    assert "User=orangepi" not in service


def test_hardware_service_follows_safe_local_settings_and_has_off_hooks():
    service = load_script("create-service").render_service(
        "/home/maker/controller", "maker", "orange-pi-zero-2w", "hardware")
    assert "Environment=KILN_BOARD=orange-pi-zero-2w" in service
    assert "KILN_SIMULATE=" not in service
    assert "ExecStartPre=" in service and "ExecStopPost=" in service
    assert service.count("heater-off.py") == 2
    assert "SupplementaryGroups=gpio" in service


def test_hardware_generator_requires_commissioning_acknowledgment(tmp_path):
    output = tmp_path / "kiln.service"
    result = subprocess.run([sys.executable, str(ROOT / "scripts/create-service.py"),
                             "--board", "raspberry-pi", "--mode", "hardware",
                             "--user", "maker", "--output", str(output)],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert "requires --commissioned" in result.stderr
    assert not output.exists()


def test_generator_refuses_to_overwrite_a_unit(tmp_path):
    output = tmp_path / "kiln.service"
    output.write_text("existing deployment")
    result = subprocess.run([sys.executable, str(ROOT / "scripts/create-service.py"),
                             "--board", "raspberry-pi", "--user", "maker",
                             "--output", str(output)], capture_output=True, text=True)
    assert result.returncode == 2
    assert output.read_text() == "existing deployment"


def test_generator_escapes_systemd_specifiers_and_dollars():
    service = load_script("create-service").render_service(
        '/home/maker/100% $dollar "quoted"', "maker", "raspberry-pi", "simulation")
    assert 'WorkingDirectory=/home/maker/100%% $dollar "quoted"' in service
    assert '100%% $$dollar \\"quoted\\"/venv/bin/python' in service


@pytest.mark.parametrize("port", ["0", "65536", "eight", "-1"])
def test_preview_rejects_invalid_ports_before_startup(port):
    result = subprocess.run(["bash", str(ROOT / "scripts/run-simulation.sh"),
                             "--port", port], capture_output=True, text=True)
    assert result.returncode == 2
    assert "Choose a port" in result.stderr


@pytest.mark.parametrize("custom_settings", [False, True])
def test_preview_locks_simulation_and_isolates_settings_and_recovery(tmp_path, custom_settings):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    launcher = scripts / "run-simulation.sh"
    launcher.write_text((ROOT / "scripts/run-simulation.sh").read_text())
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text(f"#!{sys.executable}\nimport os,json\nprint(json.dumps(dict(os.environ)))\n")
    python.chmod(0o755)
    saved = tmp_path / "settings.json"
    saved.write_text('existing Orange Pi settings')
    environment = {key: value for key, value in os.environ.items() if not key.startswith('KILN_')}
    environment["KILN_SIMULATE"] = "0"  # Preview must override any inherited real mode.
    if custom_settings:
        environment["KILN_SETTINGS_FILE"] = str(tmp_path / "custom.json")
    result = subprocess.run(["bash", str(launcher), "--port", "8099"],
                            env=environment, text=True, capture_output=True, check=True)
    actual = json.loads(result.stdout.splitlines()[-1])
    assert actual["KILN_BOARD"] == "raspberry-pi"
    assert actual["KILN_SIMULATE"] == "1"
    assert actual["KILN_PORT"] == "8099"
    assert actual["KILN_STATE_FILE"] == str(tmp_path / "storage/preview/raspberry-pi/state.json")
    expected = tmp_path / ("custom.json" if custom_settings else "storage/preview/raspberry-pi/settings.json")
    assert actual["KILN_SETTINGS_FILE"] == str(expected)
    assert saved.read_text() == 'existing Orange Pi settings'


def test_generated_service_passes_systemd_parser(tmp_path):
    analyzer = shutil.which("systemd-analyze")
    if not analyzer:
        pytest.skip("systemd-analyze is not installed on this development host")
    directory = tmp_path / "controller with spaces"
    python = directory / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    module = load_script("create-service")
    for mode in ("simulation", "hardware"):
        service = tmp_path / f"kiln-{mode}.service"
        service.write_text(module.render_service(directory, "maker", "raspberry-pi", mode))
        result = subprocess.run([analyzer, "verify", str(service)], text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
