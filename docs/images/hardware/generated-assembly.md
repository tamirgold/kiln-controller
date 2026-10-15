# Generated assembly illustrations

Created 15 October 2026 with the imagegen skill's approved API/CLI fallback,
using `gpt-image-2`. The initial parts and mounting images used high quality,
1536 × 1024 PNG. The wired overview uses a medium-quality generated base,
with connection lines and labels added locally. These illustrations cover
component recognition, mounting and low-voltage connection overviews.
They are not photographs of a completed or tested Raspberry Pi build.

Numbered markers were added locally after generation to match the Markdown
legends. The published images are JPEG web copies (quality 92); the generated
and annotated PNG originals are retained in the workspace output.

- [Parts layout](raspberry-pi-parts-generated.jpg)
- [Assembly layout](raspberry-pi-assembly-generated.jpg)
- [Wired assembly overview](raspberry-pi-wired-assembly-generated.jpg)

Use the [build guide's pin tables and schematic](../../builds/raspberry-pi.md#3-connect-the-low-voltage-parts)
for electrical connections. Component appearance and wire colors in generated
images are not a purchasing specification or polarity reference.

## Generation prompts

### 1. raspberry-pi-parts-generated.jpg

Use case: product-mockup. Asset type: photographic-style educational parts layout for a beginner GitHub build guide. Primary request: a clear top-down arrangement of the low-voltage parts for preparing a Raspberry Pi 4-based kiln controller on a light neutral workbench. Subject: one Raspberry Pi 4 Model B with a 40-pin header and recognisable USB-C, two micro-HDMI, four USB and Ethernet connectors; one microSD card with USB card reader; one matching USB-C power supply; one MAX31855 thermocouple breakout with a two-screw thermocouple terminal; one metal-sheathed K-type thermocouple with cable; a small bundle of female jumper leads; four mounting standoffs. All parts separate and unpowered. Style: realistic product-photography illustration with clear component shapes, soft daylight and restrained shadows. Enough separation to identify every part at phone size. Landscape overhead composition, grouped components, uncluttered, generous margins. Constraints: no connected wires, no kiln, no mains wiring, no SSR, no output-driver part, no invented pin labels, no logos or certification marks. Do not imply this is a complete shopping kit. No text inside the generated image; labels and generated-image disclosure will be ordinary Markdown beside it. Accurate and consistent component scale.

### 2. raspberry-pi-assembly-generated.jpg

Use case: product-mockup. Asset type: photographic-style assembly orientation image for a beginner GitHub build guide. Primary request: show how to arrange the low-voltage controller parts on a mounting plate before connecting wires. Subject: one Raspberry Pi 4 Model B secured to insulated standoffs, a separate MAX31855 sensor breakout also mounted on standoffs, a thermocouple cable entering through a strain-relief gland beside the converter, and an open empty mounting area reserved for an output interface chosen from its datasheet. A tidy open low-voltage enclosure surrounds the plate; its lid lies beside it. The Pi's USB, Ethernet and power sockets face accessible enclosure cable-entry space; the 40-pin header is clear. Component headers and screw terminals remain visible and unconnected. The thermocouple cable's loose ends rest near the sensor terminals without connecting. Power supply disconnected and out of frame. Style: realistic product-photography illustration, three-quarter overhead view, clear proportions, soft light, neutral background, practical maker workspace. Landscape with generous negative space around components; mounting points and cable entry visible. Constraints: no electrical wire connections, no heater or mains circuitry, no powered indicator lights, no output-driver design, no pin-number annotations or fabricated product marks. Do not represent a completed or tested controller. No text inside the generated image; concise labels and generated-image disclosure belong in the guide. Correct Raspberry Pi 4 layout: 40-pin header, two micro-HDMI connectors, one USB-C, four USB sockets and Ethernet.

## Assembly correction

The first assembly draft had an incorrect sensor terminal block and mounting
hardware. The selected image uses this correction, with the first assembly
draft as Image 1 and the parts layout as Image 2:

Use case: precise-object-edit.
Image 1 is the edit target: the open enclosure assembly illustration. Image 2 is a reference for the Raspberry Pi and the two-screw MAX31855 sensor breakout only.
Correct ONLY the sensor module and the mounting hardware in Image 1. Preserve the enclosure, composition, lid, cable gland, loose thermocouple leads, background, board positions, spare output-interface area, lighting and scale.
Replace the sensor board in Image 1 with the blue MAX31855 breakout from Image 2: a small blue circuit board with exactly TWO green screw-terminal positions for the thermocouple, not five positions. Put the two-terminal block nearest the loose thermocouple wires; leave both terminals and the GPIO header unconnected. Include its actual small signal header along the other edge.
Correct the mounting of both circuit boards. The Raspberry Pi has exactly four gold-ringed mounting holes in its PCB, one near each corner. Put one nylon standoff directly BELOW each actual PCB mounting hole and one small screw THROUGH that same hole from above. All four screw heads must be centered in the gold PCB mounting holes and actually secure the board. Remove every mounting screw or tall pillar that stands beside the Pi rather than passing through it. Do not add extra PCB holes. Apply the same physically correct through-hole mounting to the sensor breakout's corner holes. The PCB undersides must stay clear of the mounting plate. Do not add floating hardware.
Maintain photographic realism. No new labels, text, wiring connections, lights, mains components or other changes. This remains an unpowered arrangement BEFORE wiring, not a finished or tested controller.

## Wired assembly addition

Requested 15 October 2026: add the SSR and the connections between components.
The final image shows a Raspberry Pi, MAX31855, compatible active-low relay,
three-phase DC-input SSR on a heatsink, and separate regulated 5 V SSR-control
supply. The relay's logic/coil supply remains module-specific; its callout is
deliberately separate from the drawn SSR-control loop. AC load terminals and NC
are unused in this overview.

The first wired image draft misrouted the GPIO lead and the control loop. It was
not published. A second edit made an unwired component base. Connection paths,
the pull-up branch, terminal labels and numbered legend were drawn locally from
the guide's connection table. This overlay shows the electrical relationships;
generated component geometry is not an actual pin-position or drilling template.
The final image is a 1536 × 1184 JPEG web copy; the generated base and annotated
PNG are retained in the workspace output.

### Initial wired-image prompt

Use case: precise-object-edit. Make a polished photographic-style educational connection overview for a beginner kiln-controller build guide.
Image 1 is the edit target: the open enclosure with Raspberry Pi 4 and MAX31855 sensor. Preserve their recognizable shapes, the natural light, neutral wood workbench, perspective, enclosure, and restrained realistic style. Image 2 is a reference ONLY for the shape and terminal arrangement of the documented THREE-PHASE SSR with 3–32 VDC control input. It has six AC load terminals in three pairs plus a separate DC + and DC −. Do not copy branding or an 80 A suitability claim.
Expand/recompose the scene slightly to include the complete low-voltage CONTROL wiring. The Pi stays left; the blue MAX31855 stays upper middle. Add a small 3.3 V-compatible active-low RELAY/DRIVER module in the reserved lower-middle mounting area. This driver has separate IN1 and logic GND connections, separate module-power connector, and distinct COM / NO / NC dry-contact terminals. Remove the empty mounting-area outline. At the right, replace the loose lid with the referenced three-phase SSR mounted on an appropriately visible large finned aluminium heatsink OUTSIDE the plastic low-voltage enclosure. Keep an obvious separation between the enclosure's sensor/logic area and the SSR power stage. Add a compact insulated regulated 5 V DC control supply below/right, with a clear separate red/black low-voltage output pair, and a separate USB-C power lead connected to the Pi.
Show these tidy PHYSICAL WIRE GROUPS, with visible endpoints and minimal crossings:
1. Five fine insulated conductors in one neat harness from the Pi 40-pin header to the MAX31855 signal header: 3.3 V, GND, CLK, MISO and CS. No MOSI wire for this MAX31855. The probe cable entering through the right-hand cable gland must now terminate at the sensor's TWO thermocouple screw terminals, with exactly one lead at each terminal. The converter has exactly two thermocouple terminals.
2. A distinct orange control lead from the Pi GPIO header to relay IN1, and a gray logic-ground lead from the Pi header to relay logic GND. A small insulated 10 kΩ pull-up resistor links IN1 to the Pi's 3.3 V rail. This is GPIO to relay input ONLY: no direct GPIO-to-SSR wire.
3. The separate regulated 5 V control supply's RED +5 V lead terminates at relay COM. Relay NO goes by another RED lead to the SSR's small DC INPUT + terminal. The SSR's DC INPUT − returns by a BLACK lead directly to that same 5 V control supply's 0 V. NC is UNUSED. The red circuit runs supply → COM → NO → SSR +. It does not run through the Pi. Do not join this separate control-supply 0 V loop to Pi logic ground.
4. The relay logic/coil POWER connection is module-specific. Show a short separate power pigtail ending in a floating labelled schematic callout rather than inventing VCC/JD-VCC connections. The exact callout text is "Relay power: per module datasheet". Keep this distinct from the regulated SSR-control supply. Do not draw that unspecified lead to a Pi GPIO pin.
The SSR's six large AC LOAD terminals stay visibly UNWIRED and are behind a clear protective terminal guard. Add the exact nearby caption "AC load wiring omitted". No heater mains wiring, earth/neutral improvisation, contactor coil wiring, or live lamp. The three-phase SSR is not a little single-phase block. Its DC control wires must end at the separate small + and − terminals, never at any of the six AC terminals.
Use natural-looking color-coded low-voltage wires with connector housings; no bare loose copper, impossible connections, floating screws, merged terminals, or extra anonymous electrical parts. Do not invent numeric current ratings or approval/certification marks. The photo is a conceptual connection OVERVIEW, not a pin-position reference or a tested build. Leave generous margins for numbered markers to be added afterward. Limit in-image text to the two specified callouts and short, legible terminal labels IN1, GND, COM, NO, NC, +, − where needed. No arrows, giant explanatory paragraphs, or decorative text.

### Component-base correction prompt

Use case: precise-object-edit. Edit the supplied photographic assembly overview. Keep the same composition, perspective, enclosure, Raspberry Pi at left, blue sensor at upper middle, relay at lower middle, SSR at right, wood background and lighting. This is the component base for an educational wiring overlay that will be drawn accurately afterward.

Make ONLY these corrections:
1. Remove ALL colored interconnection wires between the Pi, sensor, relay, SSR and 5 V supply. Remove the colored five-wire sensor harness completely. Remove the orange/gray wires and their resistor, including the incorrect plug in the Pi's round 3.5 mm AUDIO socket. The audio socket must be EMPTY. Remove all red/black wires at relay COM/NO and SSR +/− and supply +5V/0V. Leave their terminal openings visible and unobstructed for the later overlay. Keep the Pi's black USB-C power cable in its correct USB-C socket, and keep the separate relay-power pigtail and its small "Relay power: per module datasheet" callout.
2. Leave the thermocouple cable coming through its gland, but disconnect its two fine ends from the sensor, letting them rest just below the blue sensor. It will be wired by the later overlay.
3. The relay must have exactly three green screw terminals, clearly and correctly labeled COM (top), NO (middle), NC (bottom), and separate IN1 and GND header pins at its left. All those five terminals are currently unwired. Its separate power pigtail remains only at its module-power connector.
4. Correct the SSR to THREE PHASES: exactly THREE large AC power studs across its upper edge and exactly THREE across its lower edge, under clear protective covers. Six large AC terminals TOTAL, never eight. Retain its separate small DC INPUT + and DC INPUT − terminals at the right side, with two visible empty connection holes. All SSR terminals remain unwired in this base image. Keep the large finned metal heatsink and the caption "AC load wiring omitted".
5. Replace the ventilated metal 5 V supply case with an insulated matte-black plastic DC supply block in the same position. Keep a single insulated power-input cable leaving the right edge. The only exposed connections on its front are two small low-voltage output terminals marked +5 V and 0 V, both unwired. No mains terminals or invented certification marks.

Do not draw any new interconnecting wires. Do not add extra components, labels, arrows or current ratings. Do not change the positions or enlarge the parts. Preserve realistic small circuit boards, correct natural shadows and readable original two callouts. The actual connections will be added separately from a verified connection map.
