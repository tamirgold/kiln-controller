# Parts and tools

[Back to the README](../README.md) · [Getting started](GETTING-STARTED.md)

Start with one board and one sensor combination. The table below describes the
parts' roles and buying requirements. It is **not a verified universal shopping
kit**: the Orange Pi installation is the existing example; the Raspberry Pi
profile still needs a physical build report. Prices and availability vary.

## Low-voltage controller

[![Generated Raspberry Pi parts layout with a MOSFET switch module, 10 kΩ resistor and white ceramic-sheathed K-type thermocouple](images/hardware/raspberry-pi-parts-generated.jpg)](images/hardware/raspberry-pi-parts-generated.jpg)

*Generated illustration of the Pi control-circuit parts, including the MOSFET
module and ceramic-sheathed probe. Use the parts table and actual module
markings when buying. The enclosure and SSR/heatsink appear in the assembled-box
guide. Independent kiln protection is listed below.*

**Parts shown:** **1** Raspberry Pi; **2** microSD card and reader;
**3** USB-C power supply; **4** MAX31855 sensor converter;
**5** ceramic-sheathed K-type thermocouple; **6** jumper leads;
**7** insulating mounting spacers; **8** MOSFET switch module;
**9** 10 kΩ pull-down resistor.

See the [Raspberry Pi build guide](builds/raspberry-pi.md) for SD-card preparation,
mounting and the exact wiring diagram.

| Qty | Part | Buying and assembly notes |
| ---: | --- | --- |
| 1 | Raspberry Pi 4B or supported Pi 3 model | Proposed Pi route; 40-pin header. Any normal memory variant is ample for the interface, but record the exact model when validating. Pi 5/400/Compute Modules/Zero are not covered by this profile. See [board status](supported-boards.md). |
| or 1 | Orange Pi Zero 2W | Existing route. Check whether the 40-pin header is supplied/soldered; it is not interchangeable with Raspberry Pi pin naming. |
| 1 | Correct board power supply | Pi 4: the manufacturer's recommended USB-C supply (5.1 V / 3 A). Pi 3: suitable micro-USB supply (typically 5.1 V / 2.5 A). Orange Pi Zero 2W: regulated 5 V supply as described in [Hardware](HARDWARE.md#2-power-the-controller). Never feed a higher voltage into GPIO. |
| 1 | microSD card | A reputable 16 GB or larger card is a practical starting choice for a Lite OS and records, not a tested lifetime/storage guarantee. Back up firing data. |
| 1 | SD reader | Needed to flash the OS from your computer. |
| 1 | MAX31855 K-type converter breakout | Use a reputable module with a published schematic and 3.3 V logic compatibility. The [Adafruit MAX31855 guide](https://learn.adafruit.com/thermocouple) explains the labeled breakout. Check whether pin headers and screw terminals need soldering. |
| 1 | Ceramic-sheathed, ungrounded K-type kiln thermocouple | Choose an electrically insulated probe with a ceramic protection tube, rated for the kiln's firing temperature and mounting. Ceramic appearance alone does not establish its rating or junction insulation. Match extension wire/connectors to type K; use T+ and T− markings, not wire color alone. |
| 1 (Pi) | MOSFET trigger switch module | Active-high, low-side output; nominal 5 V power; 3.3 V-compatible trigger safe for Pi GPIO. Switches the SSR's DC control current. Sold under names such as “MOSFET Field-Effect Transistor Trigger Switch Drive Module PWM”; check the exact module requirements below. |
| 1 (Orange Pi) | Active-low mechanical relay interface | For the recorded Orange Pi build: use its matching module schematic, supply connections and inversion setting. It is an alternative interface, not an extra part for the Pi MOSFET build. See the [Orange Pi wiring](HARDWARE.md#4-connect-the-relay-and-ssr-input). |
| 1 (Pi) | Suitable 10 kΩ resistor | Pulls the MOSFET trigger input to logic ground when GPIO is floating; check compatibility with the module's input circuit. |
| As needed | Jumper leads / terminal connectors / low-voltage wire | Useful for bench assembly, with proper permanent connectors and strain relief for the finished controller. Never use a solderless breadboard for mains. |
| 1 + fittings | Larger divided enclosure, insulating spacers and cable glands | Fit Pi/MAX31855/MOSFET on one side and SSR/heatsink on the other, with the specified cooling clearance. The ceramic probe stays outside; its lead enters the low-voltage area through a gland. Provide protected divider crossings and protective-earth bonding of exposed metal as required. |
| 1 | Local network connection | Ethernet or Wi-Fi supported by your board/OS, with a browser on a phone/computer. No separate touch screen is required. |

These inherited photographs help identify the board, sensor and connectors. They are not
photographs of a verified Raspberry Pi build of this fork.

| Raspberry Pi example | MAX31855 breakout example | Bench connectors example |
| --- | --- | --- |
| ![Example Raspberry Pi board with a 40-pin header](../public/assets/images/rpi.png) | ![MAX31855 breakout, separate headers and screw terminal](../public/assets/images/max31855.png) | ![Jumper wires, ribbon cable and solderless breadboard for low-voltage bench use](../public/assets/images/breadboard.png) |

## Choose the output interface deliberately

The [Raspberry Pi example](builds/raspberry-pi.md#heat-request-output) uses a
**MOSFET Field-Effect Transistor Trigger Switch Drive Module PWM** requiring an
**active-high 3.3 V trigger, nominal 5 V supply and low-side output**. This generic
product name is not an exact part number or evidence of compatibility. Check
that DC+ connects to OUT+ and OUT− is the return switched to DC−, and that the
trigger input neither exposes GPIO to 5 V nor draws excessive GPIO current.

The Pi's normal USB supply powers the module and SSR control input through
header pin 2 (+5 V). Include the SSR reference's **40 mA maximum input current**,
module consumption and Pi/accessory loads in the power budget. Pi ground and
module power/logic ground are common. **SSR input − goes to switched OUT−, not
directly to Pi ground**, which would bypass the switch. A suitable 10 kΩ
trigger-to-ground pull-down provides a low bias when GPIO is floating.
Leave **Invert SSR control signal off** for this active-high arrangement.
Do not add a second powered 5 V supply to the Pi header or apply 5 V to GPIO.

The documented Orange Pi assembly uses an **active-low relay interface**. Its
contacts switch regulated 5 V into a **3–32 VDC-input SSR**. The supplied SSR
reference lists up to **40 mA input current**; do not connect it directly to a
GPIO pin. Read the [relay/SSR diagram](HARDWARE.md#4-connect-the-relay-and-ssr-input).

Before buying a substitute, obtain its actual schematic/datasheet and establish:

- Input works at 3.3 V without sending higher voltage into the board.
- Supply, ground and switched-output connections, including any VCC/JD-VCC
  jumper on a relay module.
- Whether HIGH or LOW requests heat, and which setting produces OFF.
- Its output can supply/switch the SSR input current at the required voltage.
- Its OFF behavior at boot, process exit, OS shutdown and controller power loss.
  Pi header 5 V can stay energized after shutdown, and a pull-down cannot
  override a GPIO that remains HIGH.
- Its permitted switching rate. The documented mechanical relay uses a
  30-second cycle; a different interface needs appropriate timing. “PWM” in the
  MOSFET board's name does not mean high-frequency PWM should drive the AC SSR.

The current documentation does not establish an exact universally recommended
MOSFET or relay module SKU. Record the purchased module and verify its behavior
in the physical build. An input-bias resistor alone does not establish that
the output switches off under every controller fault.

## Kiln power components

Have a qualified electrician select these for the kiln's nameplate, supply and
local installation requirements. They are separate from the low-voltage kit:

- An appropriately rated single-phase or three-phase AC SSR/power stage, with
  specified heatsink, mounting and thermal interface.
- A safety contactor and independent temperature limiter with its own sensor,
  manual reset, appropriate interlocks and shutdown on relevant faults.
- Isolation, overcurrent/protective devices, correctly sized conductors,
  protective earth/bonding and a suitable enclosure.

An “80 A” label is not a universal installed-current rating. Current, phase
arrangement, cooling and protective-device selection need the real installation
details. [Hardware](HARDWARE.md#5-understand-the-three-phase-power-path) shows the
conceptual power path.

## Tools and skills

- A computer for SD flashing and a browser for the interface.
- Small screwdrivers, wire cutters/strippers and appropriate connector tools.
- A suitable meter and the ability to check **low-voltage** supply/polarity.
- Soldering tools and competence if your board/module arrives without fitted
  headers. Buy a documented preassembled version if you cannot solder reliably.
- An electrician for mains design, assembly and verification.

Read the complete build guide before cutting or connecting wires. First locate
the board's pin-1 marker. Physical header numbers and software GPIO names are
different identifiers; never count from an assumed USB-connector orientation.

## Sensor alternatives

| Converter | Thermocouple choices | Extra requirements |
| --- | --- | --- |
| MAX31855 | K for this implementation | Suitable ungrounded insulated probe; no configurable 50 Hz filter |
| MAX31856 | B, E, J, K, N, R, S, T | Connect MOSI as well; select converter and actual type in Settings; check filter and temperature range |

Converter range is not a rating for the probe, kiln, wiring or load. Set the
temperature limit within the entire system's ratings. PT100/RTD, MAX31865 and
MCP9600 are not implemented sensor choices in this build.

## Record your completed build

For a reproducible build report, photograph the assembled low-voltage controller
with labels, list the exact purchased parts and document tested pin/polarity
settings. Include clear board and module names so an attractive picture cannot
be mistaken for a wiring instruction for a different variant.
