# Board options and compatibility

Status reviewed **15 October 2026**. Support belongs to an exact board, operating
system, software version and wiring combination—not just a manufacturer name.

**Orange Pi Zero 2W is the documented deployment.** A Raspberry Pi 3/4 software
profile and installation route are now provided, but they have **not been
validated on Raspberry Pi hardware**. A Linux computer can run the simulator
without a board or sensor. See [Getting started](GETTING-STARTED.md) to choose a
route, or [Development](DEVELOPMENT.md) to try the simulator and work on a port.

## Which board should I choose?

For a build that follows existing deployment evidence, use the
[Orange Pi Zero 2W installation](INSTALL.md) and its exact wiring guide. The
[Raspberry Pi guide](builds/raspberry-pi.md) is a route for makers prepared to
validate a new hardware combination; Raspberry Pi 4 is the first proposed
beginner-build validation target.

The Pi guide specifies a MAX31855 and a ceramic-sheathed, ungrounded K-type
thermocouple rated for the kiln, plus an active-high, low-side MOSFET trigger
switch module with a 3.3 V-compatible trigger, nominal 5 V supply and 10 kΩ
trigger pull-down. The module switches the SSR's DC control input; the SSR
switches kiln power. The recorded Orange Pi deployment retains its active-low
mechanical relay interface. Each route needs its own wiring and polarity checks.

| Board | Status in this fork | What that means |
| --- | --- | --- |
| **Orange Pi Zero 2W** | **Documented deployment** | Debian 12, Python 3.11, Blinka 9.2.0; the `orange-pi-zero-2w` profile preserves the recorded H616-compatible mapping. See the [installation guide](INSTALL.md) and [deployment record](ORANGE-PI-SETUP.md). |
| **Raspberry Pi 4 Model B** | **Software route added; hardware unverified** | The `raspberry-pi` profile, Settings pin choices and installer are provided. No fresh-device installation or physical commissioning has been performed for this release. |
| Raspberry Pi 3 Model A+, 3 Model B and 3 Model B+ | Software route added; hardware unverified | Intended to use the same Pi 3/4 profile; each model, OS and output interface still needs a build report. |
| Raspberry Pi Zero 2 W | Unverified port candidate | Not covered by Pi 3/4 validation. Check the exact board, fitted header and GPIO backend before adding support. |
| Raspberry Pi Zero | Unverified port candidate | No current installation or hardware validation for this fork. |
| Raspberry Pi Zero W / WH | Unverified port candidates | Wireless and header variants do not establish software or output compatibility. |
| Raspberry Pi 2 Model B | Unverified port candidate | No current installation or hardware validation for this fork. |
| Raspberry Pi 1 Model A+, B+ | Legacy port candidates | A 40-pin header alone is insufficient; OS, dependencies and GPIO behavior need validation. |
| Raspberry Pi 1 Model A / B, including 26-pin revisions | Legacy port candidates | Require a separate pin diagram and software/dependency checks. |
| Raspberry Pi 5 | Unverified port candidate | Needs its own GPIO/backend and OS work; do not assume the Pi 3/4 path applies. |
| Raspberry Pi 400 / 500 | Unverified port candidates | No dedicated profile validation; identify the exact model and header orientation. |
| Raspberry Pi Compute Module families | Advanced port candidates | Record both the module and carrier board; power and exposed pins depend on the carrier. |
| Other Orange Pi models | Unverified port candidates | Zero 2W's forced chip mapping must not be copied to another model without verification. |
| Banana Pi, NanoPi, ODROID, Radxa / Rock Pi | Unverified port candidates | Some older models appear in the inherited inventory below; they need board profiles and complete validation. |
| BeagleBone / BeagleV, Pine64, Libre Computer, Khadas | Unverified port candidates | Blinka availability is only one prerequisite; check GPIO, SPI, OS and wiring. |
| NVIDIA Jetson, Google Coral and other Linux or industrial boards | Unverified port candidates | No maintained installation route or physical validation in this fork. |

“Software route added” means the repository has code and instructions for the
route. It does not mean GPIO timing, sensor readings, output polarity or kiln
operation have been tested on that hardware. The exact model accepted by a
profile is defined in [the hardware-profile code](../lib/board_profiles.py).
Real Raspberry Pi operation currently accepts only Pi 3 Model A+/B/B+ and Pi 4
Model B. Other Pi models need support work before the application will start.

## Other ways to run the system

| Architecture | Status | Role and limits |
| --- | --- | --- |
| Linux desktop, laptop or WSL | Software-only simulation | Run the web interface and a virtual kiln without GPIO or thermocouple packages. See [the simulator instructions](DEVELOPMENT.md#try-the-interface-without-hardware). This does not test a physical output. |
| Linux virtual machine | Simulation candidate | Uses the same Python path; validate networking and dependencies in the chosen VM. Physical GPIO is not provided by the simulator. |
| Container | Unpackaged simulation candidate | No maintained Docker image or container recipe is supplied. A container does not make host GPIO behavior portable. |
| Native Windows or macOS | Unverified development environments | The documented development commands target Linux; Windows users can use WSL. No native installation claim is made. |
| Computer + FT232H/FT2232H, Binho, GreatFET or U2IF bridge | Experimental architecture | The computer runs the server; an attached bridge supplies GPIO/SPI. This requires a new profile and validation of disconnect, startup and output-off behavior. |
| Arduino, ESP32, Raspberry Pi Pico and similar microcontrollers | Not standalone replacements | This repository is a Python application for a host operating system, not microcontroller firmware. A Pico running U2IF is a host bridge, not a standalone installation. |
| Separate networked sensor/output controller | New architecture requiring development | There is no supplied network hardware backend. It would need a protocol, fault handling, timing and independent output-off behavior. |

A browser on a phone or computer is a client of the controller. Opening the
dashboard on a device does not mean that device is running the kiln hardware.

## Historical Blinka inventory

The previous version of this page listed **68 Blinka module names** as though
they established kiln-controller compatibility. They do not. The complete list
is retained here to help identify past candidates and avoid losing references.
It is not a current list of tested boards or a guarantee that Blinka 9.2.0
supports every named device on its present operating system.

Read the [Blinka documentation](https://docs.circuitpython.org/blinka/en/latest/)
for the library's requirements, then use this project's status table and a
model-specific build report to assess this fork. Newer models absent from the
inventory need the same evidence as older ones.

<details>
<summary>Show all 68 inherited entries, grouped by family</summary>

### Raspberry Pi — 5 entries

- Raspberry Pi 1 Model B, revision 1 — `raspberrypi/raspi_1b_rev1.py`
- Raspberry Pi 1 Model B, revision 2 — `raspberrypi/raspi_1b_rev2.py`
- Generic Raspberry Pi 40-pin definition — `raspberrypi/raspi_40pin.py`
- Raspberry Pi 4 Model B — `raspberrypi/raspi_4b.py`
- Raspberry Pi Compute Module definition — `raspberrypi/raspi_cm.py`

### Orange Pi — 8 entries

- Orange Pi 3 — `orangepi/orangepi3.py`
- Orange Pi 4 — `orangepi/orangepi4.py`
- Orange Pi PC — `orangepi/orangepipc.py`
- Orange Pi R1 — `orangepi/orangepir1.py`
- Orange Pi Zero 2 — `orangepi/orangepizero2.py`
- Orange Pi Zero Plus 2 H5 — `orangepi/orangepizeroplus2h5.py`
- Orange Pi Zero Plus — `orangepi/orangepizeroplus.py`
- Orange Pi Zero — `orangepi/orangepizero.py`

The deployed Orange Pi **Zero 2W** is distinct from the inherited **Zero 2**
entry. Its current profile deliberately uses the verified common H616 pins.

### Banana Pi — 3 entries

- Banana Pi M2 Plus — `bananapi/bpim2plus.py`
- Banana Pi M2 Zero — `bananapi/bpim2zero.py`
- Banana Pi M5 — `bananapi/bpim5.py`

### NanoPi — 3 entries

- NanoPi Duo2 — `nanopi/duo2.py`
- NanoPi NEO Air — `nanopi/neoair.py`
- NanoPi NEO — `nanopi/neo.py`

### ODROID — 4 entries

- ODROID C2 — `hardkernel/odroidc2.py`
- ODROID C4 — `hardkernel/odroidc4.py`
- ODROID N2 — `hardkernel/odroidn2.py`
- ODROID XU4 — `hardkernel/odroidxu4.py`

### Radxa / Rock Pi — 4 entries

- Radxa Zero — `radxa/radxazero.py`
- Rock Pi 4 — `radxa/rockpi4.py`
- Rock Pi E — `radxa/rockpie.py`
- Rock Pi S — `radxa/rockpis.py`

### BeagleBoard — 4 entries

- BeagleBone AI — `beagleboard/beaglebone_ai.py`
- BeagleBone Black — `beagleboard/beaglebone_black.py`
- PocketBeagle — `beagleboard/beaglebone_pocketbeagle.py`
- BeagleV Starlight — `beagleboard/beaglev_starlight.py`

### Pine64 — 3 entries

- Pine64 — `pine64.py`
- Pine H64 — `pineH64.py`
- SOPine — `soPine.py`

### Libre Computer and Khadas — 3 entries

- Libre Computer AML-S905X-CC / Le Potato — `librecomputer/aml_s905x_cc_v1.py`
- Libre Computer Tritium H3 — `tritium-h3.py`
- Khadas VIM3 — `khadas/khadasvim3.py`

### NVIDIA — 8 entries

These are inherited module names, not evidence for every product variant with
the same family name. Identify the exact module and carrier in a build report.

- Clara AGX Xavier — `nvidia/clara_agx_xavier.py`
- Jetson Nano — `nvidia/jetson_nano.py`
- Jetson NX — `nvidia/jetson_nx.py`
- Jetson Orin — `nvidia/jetson_orin.py`
- Jetson TX1 — `nvidia/jetson_tx1.py`
- Jetson TX2 NX — `nvidia/jetson_tx2_nx.py`
- Jetson TX2 — `nvidia/jetson_tx2.py`
- Jetson Xavier — `nvidia/jetson_xavier.py`

### Google Coral — 2 entries

- Coral Dev Board — `coral_dev_board.py`
- Coral Dev Board Mini — `coral_dev_board_mini.py`

### Other Linux boards — 7 entries

- ClockworkPi 3 — `clockworkcpi3.py`
- DragonBoard 410c — `dragonboard_410c.py`
- Giant Board — `giantboard.py`
- HiFive Unleashed — `hifive_unleashed.py`
- LubanCat i.MX6ULL — `lubancat/lubancat_imx6ull.py`
- Onion Omega2 — `onion/omega2.py`
- Siemens IOT2050 — `siemens/siemens_iot2050.py`

### ST / Octavo Linux boards — 3 entries

- OSD32MP1 BRK — `stm32/osd32mp1_brk.py`
- OSD32MP1 RED — `stm32/osd32mp1_red.py`
- STM32MP157C-DK2 — `stm32/stm32mp157c_dk2.py`

### Host bridges — 9 entries

- Binho Nova — `binho_nova.py`
- FTDI FT2232H — `ftdi_ft2232h.py`
- FTDI FT232H — `ftdi_ft232h.py`
- GreatFET One — `greatfet_one.py`
- Feather using U2IF — `feather_u2if.py`
- ItsyBitsy using U2IF — `itsybitsy_u2if.py`
- MacroPad using U2IF — `macropad_u2if.py`
- Raspberry Pi Pico using U2IF — `pico_u2if.py`
- QT Py using U2IF — `qtpy_u2if.py`

### Other inherited device entries — 2 entries

- Feather HUZZAH — `feather_huzzah.py`
- NodeMCU — `nodemcu.py`

These last entries do not establish that the server can run on a microcontroller.

</details>

## How a board becomes a documented build

Submit a build report with the fields below. Keep “not tested” explicit; a
successful import or simulated firing is not a physical commissioning result.

```text
Board: exact model, revision, RAM and carrier/header variant
Validation date:
Repository commit:
OS image URL/version, architecture and kernel:
Python, Blinka and GPIO-library versions:
Selected hardware profile and any source changes:
Sensor converter, thermocouple type/rating and wiring diagram:
Output interface, logic voltage, polarity, supply and physical pins:
Installer result from a clean OS:
Simulation and automated test results:
Physical sensor and disconnected/faulted-sensor results:
Heat-request OFF results: idle, boot, shutdown and controller power loss
  while the output-driver supply remains energized:
Independent cutoff and kiln power installation verification:
Supervised commissioning result and limitations:
Photos, relevant logs and guide corrections:
```

Include the board marking, physical pin numbers, GPIO identifiers and connector
orientation in wiring evidence. Omit passwords, access tokens and private
network details from public reports. Validate sensor and output behavior with
kiln mains isolated; follow the [hardware guide](HARDWARE.md) for the power and
independent-protection requirements.

The maintainer can then add the demonstrated combination to the table, with a
date and linked evidence. This does not automatically validate a different OS,
board revision, output interface or sensor. See [Adding a board profile](DEVELOPMENT.md#adding-a-board-profile)
for the code and documentation that a new port needs.
