# Generated assembly illustrations

Created 15 October 2026 with the imagegen skill's approved API/CLI fallback,
using `gpt-image-2`, high quality, 1536 × 1024 PNG. These are generated
illustrations for component recognition and arranging parts before wiring.
They are not photographs of a completed or tested Raspberry Pi build.

Numbered markers were added locally after generation to match the Markdown
legends. The published images are JPEG web copies (quality 92); the generated
and annotated PNG originals are retained in the workspace output.

- [Parts layout](raspberry-pi-parts-generated.jpg)
- [Assembly layout](raspberry-pi-assembly-generated.jpg)

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
