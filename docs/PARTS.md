# Parts and tools

[Back to the README](../README.md) · [Getting started](GETTING-STARTED.md)

Start with one board and one sensor combination. The table below describes the
parts' roles and buying requirements. It is **not a verified universal shopping
kit**: the Orange Pi installation is the existing example; the Raspberry Pi
profile still needs a physical build report. Prices and availability vary.

## Low-voltage controller

| Qty | Part | Buying and assembly notes |
| ---: | --- | --- |
| 1 | Raspberry Pi 4B or supported Pi 3 model | Proposed Pi route; 40-pin header. Any normal memory variant is ample for the interface, but record the exact model when validating. Pi 5/400/Compute Modules/Zero are not covered by this profile. See [board status](supported-boards.md). |
| or 1 | Orange Pi Zero 2W | Existing route. Check whether the 40-pin header is supplied/soldered; it is not interchangeable with Raspberry Pi pin naming. |
| 1 | Correct board power supply | Pi 4: the manufacturer's recommended USB-C supply (5.1 V / 3 A). Pi 3: suitable micro-USB supply (typically 5.1 V / 2.5 A). Orange Pi Zero 2W: regulated 5 V supply as described in [Hardware](HARDWARE.md#2-power-the-controller). Never feed a higher voltage into GPIO. |
| 1 | microSD card | A reputable 16 GB or larger card is a practical starting choice for a Lite OS and records, not a tested lifetime/storage guarantee. Back up firing data. |
| 1 | SD reader | Needed to flash the OS from your computer. |
| 1 | MAX31855 K-type converter breakout | Use a reputable module with a published schematic and 3.3 V logic compatibility. The [Adafruit MAX31855 guide](https://learn.adafruit.com/thermocouple) explains the labeled breakout. Check whether pin headers and screw terminals need soldering. |
| 1 | Ungrounded, electrically insulated K-type kiln thermocouple | Probe/sheath temperature rating and mounting must suit the kiln; do not use an ordinary low-temperature oven probe. Match any extension wire/connectors to type K. Identify T+ and T− from their labels, not wire color alone. |
| 1 | GPIO-compatible output interface | Input must suit 3.3 V logic; output must drive the chosen SSR's control input. Record exact module, supply requirements, polarity and controller-power-loss behavior. See below before buying. |
| As needed | Jumper leads / terminal connectors / low-voltage wire | Useful for bench assembly, with proper permanent connectors and strain relief for the finished controller. Never use a solderless breadboard for mains. |
| As needed | Enclosure, spacers and cable glands | Keep heat, mains wiring and sensor/logic wiring separated; ground exposed metal where required. |
| 1 | Local network connection | Ethernet or Wi-Fi supported by your board/OS, with a browser on a phone/computer. No separate touch screen is required. |

These inherited photographs help identify the kinds of components. They are not
photographs of a verified Raspberry Pi build of this fork.

| Raspberry Pi example | MAX31855 breakout example | Bench connectors example |
| --- | --- | --- |
| ![Example Raspberry Pi board with a 40-pin header](../public/assets/images/rpi.png) | ![MAX31855 breakout, separate headers and screw terminal](../public/assets/images/max31855.png) | ![Jumper wires, ribbon cable and solderless breadboard for low-voltage bench use](../public/assets/images/breadboard.png) |

## Choose the output interface deliberately

The documented Orange Pi assembly uses an **active-low relay interface**. Its
contacts switch regulated 5 V into a **3–32 VDC-input SSR**. The supplied SSR
reference lists up to **40 mA input current**; do not connect it directly to a
GPIO pin. Read the [relay/SSR diagram](HARDWARE.md#4-connect-the-relay-and-ssr-input).

Before buying a substitute, obtain its actual schematic/datasheet and establish:

- Input works at 3.3 V without sending higher voltage into the board.
- Supply and ground connections, and the role of any VCC/JD-VCC jumper.
- Whether HIGH or LOW requests heat, and which setting produces OFF.
- Its output can supply/switch the SSR input current at the required voltage.
- Its output stays OFF at boot and when controller power is lost while the
  driver/SSR supply stays on.
- Its permitted switching rate. The documented mechanical relay uses a
  30-second cycle; a different interface needs appropriate timing.

The current documentation does not establish an exact universally recommended
relay-module SKU. That choice remains a build-validation item, not a “buy any
relay” instruction. A controller-powered pull-up alone cannot prove safe OFF
behavior after controller power is lost.

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
