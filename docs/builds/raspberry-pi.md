# Build with Raspberry Pi 3 or 4

[README](../../README.md) · [Parts](../PARTS.md) · [Board status](../supported-boards.md)

**Status: software profile available; physical Raspberry Pi validation pending.**
This walkthrough has a matching installer and pin profile, but it has not been
commissioned on a real Pi/driver/kiln combination. Start with simulation. The
[Orange Pi guide](../INSTALL.md) describes the existing hardware deployment.

**No Raspberry Pi yet?** You can still [try the dashboard on a Linux computer or
in Ubuntu on Windows](../GETTING-STARTED.md#try-it-before-buying-parts). Read the
steps below to understand the eventual build before buying parts.

The initial profile accepts **Pi 3 Model A+, 3 Model B, 3 Model B+, and Pi 4 Model B**
with a 40-pin header. Pi 4B is the proposed first validation build. It does not
accept Pi 5, Pi 400/500, Compute Modules or Zero-family boards; those need separate
model/backend checks. The proposed OS is **Raspberry Pi OS Lite, 64-bit, Debian 12
(Bookworm), Python 3.11**. Record the exact image and package versions during
physical validation; software tests on a Linux computer do not verify this OS image.

> Work on the low-voltage controller with power disconnected. Keep kiln mains
> isolated throughout software, sensor and output checks. A qualified electrician
> must complete and verify the kiln power and independent safety circuit.

**The build in this guide:** a Raspberry Pi, MAX31855 sensor converter, MOSFET
switch module and SSR/heatsink share one larger divided enclosure. The
ceramic-sheathed K-type thermocouple stays outside the electronics box. The Pi's
normal USB supply powers the control circuit, including the MOSFET and SSR input through
the Pi's 5 V header; no separate SSR-control supply is needed.

## 1. Prepare the SD card and connect

You need the [listed parts and tools](../PARTS.md), a computer with an SD reader,
and access to the same local network as the Pi. Start with the board, SD card and
board power supply only; leave the driver and kiln power disconnected.
Use the correct supply for your board: USB-C for Pi 4, micro-USB for Pi 3;
see the [power-supply requirements](../PARTS.md#low-voltage-controller).

[![Generated Raspberry Pi parts layout with a MOSFET switch module, 10 kΩ resistor and white ceramic-sheathed K-type thermocouple](../images/hardware/raspberry-pi-parts-generated.jpg)](../images/hardware/raspberry-pi-parts-generated.jpg)

*Generated illustration of the Pi control-circuit parts, including the MOSFET
module and ceramic-sheathed probe. Start with the Pi, card and USB supply for
software setup; use the other components in step 3. The enclosure and SSR/heatsink
appear in the assembled view below. Use actual module markings when buying.*

**Parts shown:** **1** Raspberry Pi; **2** microSD card and reader;
**3** USB-C power supply; **4** MAX31855 sensor converter;
**5** ceramic-sheathed K-type thermocouple; **6** jumper leads;
**7** insulating mounting spacers; **8** MOSFET switch module;
**9** 10 kΩ pull-down resistor.

1. Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your
   computer. Select your exact Pi model. For the **Bookworm 64-bit Lite** image
   used by this guide, download
   `2025-05-13-raspios-bookworm-arm64-lite.img.xz` from the
   [official Raspberry Pi image archive](https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2025-05-13/).
   In Imager's operating-system chooser, select **Use custom** and choose the
   downloaded `.img.xz` file; you do not need to unpack it. This selects Debian 12
   even if Imager's default is a newer release. The image is a setup target, not
   a physically validated installation of this project.
2. Select the SD card carefully: writing the image erases the selected card.
3. Set a hostname such as **kilnpi**, create your own username/password, configure
   Wi-Fi/country if needed, and enable SSH (remote terminal access). Wired Ethernet
   can simplify the first connection on boards that provide it.
4. Write the image, eject the card, insert it into the unpowered Pi, connect the
   network and correct power supply, and allow first boot to finish.
5. Open **Terminal** on macOS/Linux, or **PowerShell/Windows Terminal** on Windows.
   Connect using the username you created. For an example username `maker`:

   ```bash
   ssh maker@kilnpi.local
   ```

   Substitute your actual username/hostname. On the first connection, compare
   the host identity through your trusted local setup before accepting it, then
   enter the password. Password typing may not show characters.

**Check:** the terminal prompt belongs to the Pi. Run:

```bash
cat /proc/device-tree/model
cat /etc/os-release
python3 --version
hostname -I
```

You should see the intended model, Debian 12-based Raspberry Pi OS, Python 3.11,
and the Pi's address. The installer checks model identity before hardware setup.

**If `.local` does not work:** find the Pi in your router's connected-device list
or on an attached local screen, then use `ssh maker@<Pi-IP-address>`. Replace the
placeholder; do not type the angle brackets. A wrong username or Wi-Fi setup
must be resolved before installing the controller.

## 2. Install and open the preview

These commands now run **on the Pi**, as your normal user:

```bash
sudo apt update
sudo apt install git
git clone https://github.com/tamirgold/kiln-controller.git
cd kiln-controller
bash setup.sh --board raspberry-pi
```

The installer prepares Python, the Raspberry Pi dependencies and GPIO access. It
creates local settings only if absent: simulation is on, recovery is off and
the initial control cycle is 30 seconds. It does not configure or start a service.
It does not decide the output polarity for your driver.

Log out with `exit`, reconnect through SSH, then:

```bash
cd kiln-controller
KILN_BOARD=raspberry-pi bash scripts/run-simulation.sh
```

Open `http://kilnpi.local:8081/picoreflow/index.html` on a phone/computer on the
same network. Use the Pi's IP if the name does not resolve.

**Check:** the page identifies a simulated kiln. Try a sample schedule to learn
the controls. The preview does not use real GPIO; successful simulation does not
prove the sensor or output driver is connected correctly. End the simulated
firing and press Ctrl+C in the SSH terminal before continuing.

**If installation fails:** keep the first error, verify your OS/model and review
the [development/setup notes](../DEVELOPMENT.md). Do not force Blinka to identify
the Pi as an Orange Pi. GPIO imports use the real board identity.

## 3. Connect the low-voltage parts

Disconnect all controller power before assembly or wiring.

[![Generated conceptual Raspberry Pi, sensor, MOSFET switch and SSR assembly in one larger divided enclosure, with the thermocouple probe outside, using Pi header 5 V](../images/hardware/raspberry-pi-wired-assembly-generated.jpg)](../images/hardware/raspberry-pi-wired-assembly-generated.jpg)

*Generated assembly with a wiring overlay. The Pi, sensor and MOSFET module sit
on one side of the divider; the SSR and heatsink sit on the other. The probe is
outside, with its cable entering through a gland. Use the pin and connection
tables for wiring and the actual parts for mounting dimensions. The SSR's AC
load terminals are shown unwired.*

**1** Raspberry Pi · **2** MAX31855 · **3** MOSFET switch module ·
**4** SSR and heatsink · **5** Ceramic-sheathed K-type thermocouple.

### Arrange and mount the parts

Gather the four modules shown above, the ceramic-sheathed thermocouple, a
suitable 10 kΩ pull-down resistor, the enclosure/divider, insulated standoffs, cable glands
and low-voltage connectors. Check the [MOSFET requirements](#heat-request-output)
before choosing its mounting holes or wiring. This Pi build uses a MOSFET
switch module in place of the Orange Pi example's mechanical relay.

1. **Choose a box that fits the actual parts.** Allow room for all four modules,
   their connectors, cable bends and the SSR's specified heatsink and cooling
   clearance. The illustration does not set the box dimensions or validate its
   cooling. Keep the electronics enclosure outside the hot kiln chamber.
2. **Separate the two areas.** Put the Pi, MAX31855 and MOSFET module in the
   low-voltage area. Put the SSR and its heatsink in the adjacent power area,
   with a suitable divider and cooling arrangement. Keep the Pi's power, network,
   USB ports and microSD slot accessible; position the converter away from heat.
3. **Mount the boards and SSR.** Secure the Pi, converter and MOSFET module
   through their own mounting holes on correctly sized insulated standoffs.
   Keep their undersides clear of the mounting plate and loose metal. Fit the
   SSR to its heatsink using its specified thermal interface and fasteners.
   Use the actual parts as drilling templates; leave all terminals accessible.
4. **Fit the cable entries.** Route the Pi's USB power lead into the low-voltage
   area. Keep the thermocouple probe outside the box and bring its lead through
   a separate strain-relief gland in that same area, directly toward the MAX31855.
   Route the two SSR control wires through a protected opening in the divider;
   keep them separate from the eventual mains wiring.
5. **Connect the control circuit using the tables below.** Wire the sensor,
   Pi-powered MOSFET module, pull-down resistor and SSR's DC input. The SSR's
   AC load terminals stay unconnected during these checks. Label the cables
   and inspect each connection before restoring USB power in step 4.

The probe lies on the workbench in the illustration to show it clearly. Its
final sensing position is in the kiln, using its specified mounting and
insulation; the converter and control box remain outside. The electrician
completes the power-area wiring and protective earth in step 5.

Locate **pin 1 from the board's marking**. Use the schematic and pin tables below
for every electrical connection; the generated image shows the arrangement and
connection overview, not exact pin positions. The diagram is a schematic and
pin locator; it is not a photograph of a verified assembly. A board's orientation
on your bench can differ.

[![Raspberry Pi 3/4 physical-pin locator and MAX31855 sensor/output connections](../images/hardware/raspberry-pi-wiring.svg)](../images/hardware/raspberry-pi-wiring.svg)

### Temperature sensor

| Physical Pi pin | GPIO / software name | Connect to |
| ---: | --- | --- |
| 1 | 3.3 V supply | Compatible MAX31855 VIN/VCC |
| 6 | Ground | MAX31855 GND |
| 23 | BCM11 / `D11` | MAX31855 CLK/SCK |
| 21 | BCM9 / `D9` | MAX31855 DO/SO/MISO |
| 24 | BCM8 / `D8` | MAX31855 CS |
| 19 | BCM10 / `D10` | Leave unconnected for MAX31855; MOSI/SDI for MAX31856 |

This profile uses **software SPI** (the application drives these signal pins);
you do not need to enable a separate hardware SPI overlay for this route. Keep
other processes from using the same pins. Physical pin numbers are not BCM
numbers: physical 23 is BCM11, not BCM23.

Connect a **ceramic-sheathed, ungrounded, electrically insulated K-type kiln
thermocouple** to T+ and T−. Its protection tube and assembly must be rated for
the firing temperature. Use the correct type-K extension cable/connector. Keep
the probe insulated from elements and the converter away from the hot chamber
and mains wiring.
Module markings govern: on Adafruit breakouts **3Vo is an output**, not VIN.

### Heat-request output

This example uses a **MOSFET Field-Effect Transistor Trigger Switch Drive Module
PWM** that must meet these requirements: **active-high, 3.3 V-compatible trigger,
nominal 5 V supply, and low-side switching**. Its DC+ supply terminal connects
internally to OUT+; it switches OUT− to DC− when triggered. The generic product
name does not establish these properties. Check the exact module's schematic,
input current and terminal markings before following this example; an input
pulled up to 5 V is unsuitable for direct Pi GPIO connection.

| Physical Pi pin | GPIO / software name | Connect to |
| ---: | --- | --- |
| 2 | +5 V supply rail | MOSFET module DC+ |
| 14 | Ground | MOSFET module DC− |
| 37 | BCM26 / `D26`, 3.3 V logic | MOSFET module TRIG / PWM input |
| 39 | Ground | Module logic GND, if provided separately |

The module's power and logic grounds share the Pi ground in this example.
Use its schematic to identify them; terminal positions and labels vary.
**Physical pin 2 supplies power; physical pin 37 carries only a 3.3 V signal.**
Never connect 5 V to a GPIO signal pin. Do not connect the documented
up-to-40 mA SSR input directly to GPIO. The
[parts guide](../PARTS.md#choose-the-output-interface-deliberately) lists the
module requirements.

The Pi's normal USB power supply also powers this **3–32 VDC SSR control input**
through the header and MOSFET module. No separate SSR-control supply is used.
Allow for the SSR reference's **40 mA maximum input current**, the module's own
consumption, and all Pi/accessory loads when checking the supply and wiring
budget. Do not connect an additional powered 5 V supply to the header.

| From | To |
| --- | --- |
| Module OUT+ (connected internally to DC+) | SSR DC control input + |
| Module OUT− (switched return) | SSR DC control input − |
| Module TRIG / PWM input, through a suitable 10 kΩ pull-down resistor | Module logic GND |

**Do not connect SSR input − directly to Pi GND:** that would bypass this
low-side switch. The current path when ON is Pi +5 V → DC+ / OUT+ → SSR input +
→ SSR input − → OUT− → the module's MOSFET → DC− / Pi GND. Only the SSR's DC
control terminals connect to this circuit; its AC load terminals remain separate.

The 10 kΩ pull-down holds TRIG low when GPIO is floating; verify it suits the
module's input circuit. It cannot override an actively driven HIGH signal.
For this active-high module, **LOW means no heat request and HIGH requests heat**;
leave **Invert SSR control signal off** (`gpio_heat_invert = False`).
The word “PWM” in the module's name does not call for high-frequency PWM here:
the controller uses timed ON/OFF heat requests for the AC SSR.

**Check before power:** match every connection to the table and actual terminal
labels. Confirm the 10 kΩ resistor goes from TRIG to logic GND, the SSR's
negative input goes only to switched OUT−, and no loose strands or fasteners
can touch the boards. Secure the cables and strain relief; temporary bench
jumper wires are not a finished enclosure installation.

## 4. Check sensing, polarity and OFF behavior

Kiln mains remain isolated. Reapply only the appropriate controller/low-voltage
power. Stop all controller processes before the sensor-only test:

```bash
KILN_BOARD=raspberry-pi KILN_SIMULATE=0 \
  timeout 15 venv/bin/python -u test-thermocouple.py
```

**Check:** the converter reports a plausible room temperature and reacts when
the probe is gently warmed. This command reads real hardware even if your saved
settings select simulation. It does not intentionally operate the heat output.
`timeout` ends it after 15 seconds (exit status 124 is expected at the timeout).
Resolve sensor faults before proceeding.

Next open a commissioning session that uses the normal local settings. A new
install's local settings still select simulation:

```bash
KILN_BOARD=raspberry-pi venv/bin/python kiln-controller.py
```

Review **Settings → Sensor & wiring**. Match every pin to the table and set
**Invert SSR control signal** according to the actual driver:

- The active-high MOSFET module described here: leave it **off**; LOW is the
  no-heat level (`gpio_heat_invert = False`).
- A different, verified active-low interface: enable it; HIGH is the no-heat
  level. Its wiring must follow its own schematic.

Review the control cycle for the driver and SSR. The installer retains a
conservative 30-second initial cycle; this does not require a mechanical relay.
Choose any later timing change for the actual SSR and kiln during commissioning;
do not configure high-frequency PWM merely because the MOSFET board accepts it.
Leave recovery and all protection overrides disabled during commissioning.
Save, review, and apply while idle. A terminal-launched process exits on apply;
rerun the same command to load the saved values.

Before allowing real heat, verify with mains isolated:

1. With simulation turned off and a ready sensor, an idle controller requests
   no heat and the driver/SSR input agrees.
2. Start/stop a suitable bench test only as part of a planned output check;
   establish which electrical levels turn the request on and off.
3. Confirm the output is off during boot, process exit, shutdown and controller
   power loss. **The Pi's 5 V header rail can remain energized after OS shutdown**:
   check the SSR input while that rail is still present, and again when USB
   power is removed. A pull-down helps only when the GPIO is not driving HIGH;
   neither it nor a stopped process proves a faulted controller will switch off.
4. Confirm a disconnected/faulted sensor prevents heating and produces a fault.

The service and software OFF calls are useful checks, not a substitute for
hardware that fails off. An SSR LED only indicates its control input. Never use
the general output-toggle script as a routine check on a powered kiln.

## 5. Complete the power installation and optional service

Have the electrician complete the enclosure's power compartment and verify
the kiln's power circuit, protective-earth bonding of exposed metal, separation
from the low-voltage area, SSR cooling in the chosen enclosure, isolation,
stop/interlock chain and independent temperature limiter
with its own sensor and manual reset. The [power diagram](../HARDWARE.md#5-understand-the-three-phase-power-path)
is conceptual; use actual nameplate and installation ratings.

After reviewing the wiring and OFF checks, generate a service for your actual
username, path and board. Stop the terminal controller first. This command
**only creates a file for review**:

```bash
mkdir -p storage/installation
python3 scripts/create-service.py --board raspberry-pi --mode hardware \
  --commissioned --output storage/installation/kiln-controller.service
cat storage/installation/kiln-controller.service
```

Check its `User`, `WorkingDirectory`, executable paths and `KILN_BOARD`. Install
it only for this commissioned build:

```bash
sudo install -m 0644 storage/installation/kiln-controller.service \
  /etc/systemd/system/kiln-controller.service
sudo systemctl daemon-reload
sudo systemctl enable --now kiln-controller
sudo systemctl status kiln-controller --no-pager
```

The hardware-capable unit follows your saved Simulation setting. Keep that on
until you are ready for the final checks; it does not force real operation.
When idle, disable simulation through Settings, review/save/apply, and verify
fresh real sensor readings and no heat request before a firing.

## 6. Commission a first firing

Set the actual kiln power, tariff, temperature limit and suitable control
settings. Default limits and PID gains are examples, not calibration results
for your kiln. Choose a supervised commissioning program suitable for the kiln
and load, and follow the electrician's test plan.

**Check:** heating stops when commanded, measured temperature behaves as
expected, independent trips work as designed, SSR operating temperature stays
within its cooling design, and the saved firing record is credible. Review
[control and recovery](../CONTROL.md) before enabling automatic restart.

Record the Pi model, OS image, package versions, exact parts, wiring and test
results in a [build report](../supported-boards.md). A completed physical report
is required before this guide can be labeled a validated Raspberry Pi build.

For everyday operation, see [Using your kiln](../USER-GUIDE.md). For changes to an
existing controller, use [Maintenance](../MAINTENANCE.md) and update only while
the kiln is idle.
