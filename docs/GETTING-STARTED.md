# Start here: from a preview to your first build

[Back to the README](../README.md)

You can explore the software before buying parts. When you are ready for hardware,
follow one complete board guide so the pins, software and checks agree.

## Try it before buying parts

This preview runs a virtual kiln on a Linux computer or Linux VM with Python 3.10
or newer. Windows users can use Ubuntu in WSL; the commands below run in that
Ubuntu terminal. The preview does not import GPIO libraries or control real pins.
Native Windows/macOS installation is not covered by this walkthrough.

On Debian/Ubuntu, open a terminal and install Git if it is missing:

```bash
sudo apt update
sudo apt install git
git clone https://github.com/tamirgold/kiln-controller.git
cd kiln-controller
bash setup.sh --board simulation
bash scripts/run-simulation.sh
```

Run setup as your normal user; it requests `sudo` for system packages. It creates
the Python environment and an initial simulation configuration, preserves existing
settings, and does not start a system service.

Open [the local dashboard](http://localhost:8081/picoreflow/index.html) in your
browser. **Check:** the page identifies simulation. Choose a sample program,
review it and start it to see a virtual temperature curve. This is a software
demonstration, not a firing recipe for your kiln.

Choose **Stop firing** to end the simulated program, then press **Ctrl+C** in the
terminal. Saved simulated records are separate from real firing records. The
launcher uses separate preview settings and recovery files for each board
profile and forces simulation for the
entire process, so it cannot be turned into a hardware session in Settings.

If port 8081 is in use:

```bash
bash scripts/run-simulation.sh --port 8082
```

Then open `http://localhost:8082/picoreflow/index.html`. Do not stop another running
controller to make room for a preview. On an existing installation, use a separate
clone for experiments; the preview still shares that clone's saved programs
and simulated firing archive. Its settings are separate unless you explicitly
provide a different `KILN_SETTINGS_FILE`.

**If the page does not open:** check that the terminal process is still running,
look at its last error, and use the port you selected. From another computer,
replace `localhost` with the Linux computer's local IP address. A WSL VM's network
access depends on its Windows/WSL network configuration; start with the browser
on the same computer.

## Choose a hardware route

| Your board | Guide | What has been demonstrated |
| --- | --- | --- |
| Raspberry Pi 3 / 4 | [Raspberry Pi build](builds/raspberry-pi.md) | Software profile and simulated checks; physical board validation is pending |
| Orange Pi Zero 2W | [Orange Pi installation](INSTALL.md) + [hardware diagrams](HARDWARE.md) | Existing Debian 12 / Python 3.11 deployment |
| Another model | [Board compatibility](supported-boards.md) | Exact-model evidence is required; many entries are only port candidates |

The Raspberry Pi walkthrough is the intended main maker path. Its current
**hardware-unverified** status means it is not yet a tested shopping-and-build
recipe. Use the Orange Pi documentation for the existing deployment example.

## Gather the parts and tools

Read [the parts list](PARTS.md) before ordering. It identifies the sensor,
power supply, connectors, soldering decisions and kiln-power components.
The Pi build uses a MAX31855 with a **ceramic-sheathed, ungrounded K-type kiln
thermocouple**, an **active-high MOSFET trigger switch module** with a
**3.3 V-compatible trigger, nominal 5 V supply and low-side output**, and a
**10 kΩ trigger pull-down resistor**. Choose a probe rated for the kiln and
firing temperature, and check the exact MOSFET module against the Pi guide.

The MOSFET switches the SSR's DC control input; the SSR switches kiln power.
The Pi's USB supply powers the MOSFET and SSR input through its 5 V header,
so this arrangement needs no separate SSR-control supply. The recorded Orange
Pi deployment uses its active-low mechanical relay interface; follow its own
wiring guide. Substitutes need electrical verification.

Keep the controller, sensor converter and power supplies outside the hot chamber.
The Pi arrangement fits the Pi, MAX31855 and MOSFET on one side of a larger
divided enclosure, with the SSR and heatsink on the other. The thermocouple
probe stays outside the electronics box and its lead enters through a gland;
its final sensing position is in the kiln. Keep mains and low-voltage wiring
separated. Your electrician selects the switching, cooling and protection
for the actual kiln.

## Follow these six steps

1. **Prepare the SD card.** Follow your board guide's OS, account and network
   instructions. Success means you can log in to the board.
2. **Install and preview.** Select the correct setup profile and open simulation.
   Success means the web page shows simulated readings.
3. **Assemble the low-voltage parts.** Disconnect power and follow the exact pin
   diagram for your board. Success means every wire matches a signal and physical
   pin number in the guide.
4. **Check the sensor and output.** Keep kiln mains isolated. Verify a plausible
   sensor reading, driver polarity, fault response and output-off behavior during
   boot, shutdown and loss of controller power. Success means the heat request
   behaves as specified even if the driver supply remains energized.
5. **Verify the kiln power and safety circuit.** A qualified electrician checks
   the SSR, heatsink, contactor, independent high-limit sensor/limiter, isolation,
   protection, earthing and applicable interlocks. Software cannot substitute
   for this circuit.
6. **Commission the first firing.** Set the actual kiln's ratings and limits,
   keep protection overrides disabled, and perform a supervised commissioning
   run. Success means you can inspect a saved, credible temperature curve.

## Learn the everyday controls

- [Using the dashboard, programs and firing history](USER-GUIDE.md)
- [Changing settings through review, save and apply](SETTINGS.md)
- [Making backups and installing updates](MAINTENANCE.md)
- [Understanding catch-up, heating control and recovery](CONTROL.md)

Keep browser control on a trusted local network. The server currently has no
user login; do not forward its HTTP port to the Internet.
