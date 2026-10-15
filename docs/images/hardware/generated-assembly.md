# Generated assembly illustrations

Created 15 October 2026 with the imagegen skill's approved API/CLI fallback,
using `gpt-image-2`. The initial parts and mounting images used high quality,
1536 × 1024 PNG. The current ceramic-probe parts image and MOSFET wired
overview use medium-quality generated bases,
with connection lines and labels added locally. These illustrations cover
component recognition, mounting and low-voltage connection overviews.
They are not photographs of a completed or tested Raspberry Pi build.

Numbered markers were added locally after generation to match the Markdown
legends. The published images are JPEG web copies (quality 92); the generated
and annotated PNG originals are retained in the workspace output.

- [Parts layout](raspberry-pi-parts-generated.jpg)
- [Assembly layout](raspberry-pi-assembly-generated.jpg)
- [Wired assembly overview](raspberry-pi-wired-assembly-generated.jpg)

The current wired overview uses the Raspberry Pi's 5 V header supply and a
generic active-high, 3.3 V-compatible low-side MOSFET trigger switch module.
It has no separate SSR-control supply or mechanical relay. The exact purchased
module must meet the build guide's requirements; the image is not a verified
product photograph. All four modules share one larger enclosure, with the
thermocouple probe outside via a cable gland. Earlier layouts and prompts
below are retained as history.

Use the [build guide's pin tables and schematic](../../builds/raspberry-pi.md#3-connect-the-low-voltage-parts)
for electrical connections. Component appearance and wire colors in generated
images are not a purchasing specification or polarity reference.

## Generation prompts

### 1. Original parts layout (superseded)

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

## Earlier relay wiring overview (superseded)

Requested 15 October 2026: add the SSR and the connections between components.
That version showed a Raspberry Pi, MAX31855, compatible active-low relay,
three-phase DC-input SSR on a heatsink, and separate regulated 5 V SSR-control
supply. The relay's logic/coil supply remains module-specific; its callout is
deliberately separate from the drawn SSR-control loop. AC load terminals and NC
are unused in this overview.

The first wired image draft misrouted the GPIO lead and the control loop. It was
not published. A second edit made an unwired component base. Connection paths,
the pull-up branch, terminal labels and numbered legend were drawn locally from
the guide's connection table. This overlay shows the electrical relationships;
generated component geometry is not an actual pin-position or drilling template.
That version used a 1536 × 1184 JPEG web copy; the generated base and annotated
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

## Earlier Pi-powered MOSFET layout (superseded)

Requested 15 October 2026: use the Raspberry Pi's 5 V supply and replace the
mechanical relay with a MOSFET trigger switch module. The edit used the earlier
unwired component base as its input, preserving the Pi, sensor and SSR while
removing the external supply and replacing the relay. It used `gpt-image-2`,
medium quality, 1536 × 1024, through the approved imagegen API/CLI fallback.

Wires and labels were added locally from the guide's connection map. The
illustrated module must be an active-high, 3.3 V-compatible, nominal-5 V,
low-side switch: DC+ feeds OUT+, and the MOSFET switches OUT− to DC−.
Pi physical pin 2 supplies DC+; pin 14 supplies the DC− ground return;
pin 37 / BCM26 supplies TRIG; pin 39 supplies the separate logic GND.
A 10 kΩ pull-down branches from TRIG to logic GND. OUT+ and OUT− connect
only to the SSR's DC + and −, respectively. The SSR negative input does not
connect directly to Pi ground. No GPIO signal is powered from 5 V.

The final image is a 1536 × 1064 JPEG, with the wiring and numbered legend
overlaid on a cropped generated base. Terminal positions are illustrative;
the pin table, schematic and actual module documentation govern assembly.
The unannotated base and annotated PNG are retained in the workspace output.
This replaces the relay/separate-supply version at the same published path.

### MOSFET replacement prompt

Use case: precise-object-edit.
Asset type: photographic-style component base for a beginner Raspberry Pi kiln-controller assembly guide. This base will receive an exact wiring overlay afterward.
Image 1 is the edit target, an unwired generated controller layout. Preserve the composition, camera, light, Raspberry Pi at left, blue MAX31855 above middle, gray enclosure and wood workbench. Preserve the three-phase DC-input SSR at right on its finned aluminium heatsink, its SIX large AC load terminals under clear guards, and the separate small DC + and DC - terminals. Keep the Pi's black USB-C power lead connected correctly.

Make these two changes:
1. Replace ONLY the blue mechanical relay board inside the enclosure with a compact blue MOSFET Field-Effect Transistor Trigger Switch Drive Module PWM, in the same lower-middle footprint and orientation. It must look like a small logic-level MOSFET switch module, with two flat black MOSFET packages and small supporting electronics, NO cube relay. The conceptual module has six separate connection positions: a two-position input power terminal at its TOP edge marked DC+ and DC-, a small two-position signal header at its LEFT edge marked TRIG and GND, and a two-position green screw terminal at its RIGHT edge marked OUT+ and OUT-. Keep every connection visibly separate. The two right output screw terminals should occupy approximately the previous COM and NO positions; there is no third NC terminal. Mount the module through its PCB mounting holes on short standoffs. Remove the previous relay power pigtail, its connector, and the entire 'Relay power: per module datasheet' paper callout. Do not invent a current rating, certification mark or exact brand/model number.
2. Completely remove the external black 5 V supply block from the lower right, including its input cable and any labels. Restore the natural bare wood workbench in its place. The Pi's USB power lead remains the only incoming control-power cable. Preserve the blank area for a later explanatory wiring legend.

Do NOT draw any interconnecting wires. Keep the Pi header, sensor signal contacts, MOSFET terminals and SSR DC input terminals empty for the later accurate wiring overlay. Keep the two loose thermocouple lead ends resting below the sensor, as in the input. Keep the nearby text 'AC load wiring omitted'. Preserve all unrelated parts and their exact positions as closely as possible; do not change the Pi or sensor connector counts. There must be no mechanical relay, no external low-voltage supply block, no relay pigtail, and no stray old wiring or labels. This is a generated conceptual illustration, not a photograph or pin-position reference for a tested build.

## Current larger-enclosure layout

Requested 15 October 2026: put the Raspberry Pi, MAX31855, MOSFET module and
SSR/heatsink together inside one larger enclosure, and show the thermocouple
outside it. The generated edit enlarges the shared box, adds an internal divider
beside the SSR compartment and depicts the probe lead through a cable gland in
the low-voltage compartment. The Pi-powered active-high MOSFET connection map
is unchanged. The SSR's AC load terminals remain unwired.

The previous unannotated MOSFET component base was the edit target, supplied
as a JPEG. The approved imagegen API/CLI fallback used `gpt-image-2`, medium
quality and 1536 × 1024 output. A second targeted edit completed the continuous
internal thermocouple cable and its two sensor-terminal connections without
changing the layout. Connection lines and numbered markers were
added locally, including marker 5 for the external K-type thermocouple.
The published JPEG is 1536 × 1184; the generated base and annotated PNG
remain in the workspace output. The divider, air space and vents illustrate
layout intent, not a verified thermal or electrical enclosure design.
Pin tables, actual module documentation and physical commissioning remain
the assembly references.

### Larger-enclosure edit prompt

Use case: precise-object-edit.
Asset type: photorealistic-style generated component layout for a beginner Raspberry Pi kiln-controller assembly guide.
Image 1 is the edit target and component reference: Raspberry Pi 4, MAX31855, MOSFET switch module, and three-phase DC-input SSR on its aluminium heatsink. Keep these same four recognizable components, their correct connector counts and the warm natural workbench lighting. This edit changes the enclosure and probe placement; it must not change the type of driver or introduce another power supply.

Primary request: put ALL four components together INSIDE ONE larger open rectangular enclosure, and show the thermocouple probe OUTSIDE that enclosure. Recompose as needed, with a slightly higher viewing angle so all components and terminals remain visible. Use a generously sized light-gray powder-coated metal enclosure with a mounting backplate. The Raspberry Pi stays in the left area, the blue MAX31855 above the middle-left area, and the blue MOSFET module below it. Put the complete SSR AND its large finned heatsink in the right-hand area, fully within the perimeter walls. Leave clear air space around the heatsink, visible louvers in the right-hand outer wall, and a simple internal insulating divider between the SSR power compartment and the Pi/sensor compartment. This is ONE common outer enclosure, not two separate boxes. Mount the small boards through their real mounting holes on short standoffs. Keep the outer enclosure completely visible and leave workbench space below it for the external thermocouple. The lid is removed and out of frame.

Move the thermocouple cable gland to the FRONT wall of the low-voltage compartment, well away from the SSR compartment. A continuous braided thermocouple lead must pass through that actual gland to a clearly visible long ceramic-sheathed K-type kiln thermocouple lying OUTSIDE the box on the foreground workbench. Show its slender white ceramic probe, metal transition ferrule and the attached braided lead as ONE coherent probe assembly. Inside the box, the cable runs toward the MAX31855 and splits into exactly two short insulated loose ends resting beside the sensor's two green thermocouple terminals. Do not use a bare wire loop as the probe and do not put the thermocouple's sensing tip inside the electronics box.

This is an UNWIRED COMPONENT BASE for a separate accurate wiring overlay. Do not draw any Pi-to-module or module-to-SSR interconnection wires. Keep all module electrical terminals empty and visible. Keep ONLY the Pi's black USB-C incoming power cable plugged into its actual USB-C socket, and the continuous thermocouple cable/probe described above. Remove the old gland in the previous small-box right wall; do not let the probe cable enter through the SSR compartment. No separate 5 V supply, no mechanical relay, no resistor yet, no old paper labels or caption 'AC load wiring omitted' on the workbench.

Component invariants:
- Raspberry Pi: one recognizable Pi 4 with its 40-pin GPIO header accessible and correct USB-C power socket, not a cable in the audio socket.
- MAX31855: one small blue converter with exactly TWO green thermocouple screw terminals and five distinct accessible signal contact positions. No extra sensor board.
- MOSFET module: one small blue board with two FLAT black MOSFET packages, not a cube relay. Two supply terminals marked DC+ and DC-, two separate logic positions TRIG and GND, and two output terminals OUT+ and OUT-. Exactly six connection positions, no NC or COM terminals. Keep input, supply and output connections clearly separated.
- Three-phase SSR: exactly THREE large AC studs across its upper edge and THREE across its lower edge, SIX AC terminals TOTAL, with transparent terminal guards. Two separate small DC control-input terminals marked + and - remain accessible. All six AC terminals stay UNWIRED. Preserve the complete finned heatsink beneath it. No current rating, branding, certification marks or mains wiring.

Use realistic materials, coherent perspective and uncluttered assembly. Avoid decorative tools, floating fasteners, spare boards, extra power blocks, captions, diagrams, number markers or arrows. The generated image is a conceptual arrangement, not a tested thermal or electrical enclosure design. Wires and explanatory labels will be added separately afterward.

### Internal probe-cable correction prompt

Use case: precise-object-edit. Change ONLY the internal thermocouple cable in Image 1; preserve every component's position, the large common enclosure and divider, SSR/heatsink, external white ceramic probe and the entire external braided cable exactly.

The external probe already connects through the front-wall gland correctly. Complete the SAME continuous braided cable INSIDE the low-voltage compartment: from the gland, route it across clear backplate to the left of the MOSFET module, then through the narrow clear gap ABOVE the MOSFET module and BELOW the Raspberry Pi, then up toward the bottom of the MAX31855 sensor board. It must not pass beneath or across any PCB and must not enter the SSR compartment. End the braid immediately below the sensor's two-position green thermocouple terminal block. From the braid, exactly TWO short insulated conductors enter the TWO thermocouple terminals, one per terminal. Remove the existing disconnected loose wire tails by the sensor and the dead-ended cable behind the MOSFET. Show one continuous connected probe/cable assembly from the external sensing tip to the sensor input. No loose or exposed bare wire ends.

Keep this the only electrical cable connection in the base image except the existing Pi USB-C power lead. Do not add GPIO wires, MOSFET power/trigger/output wires, an external supply, a relay, labels, markers or any other objects. The six SSR AC terminals remain unwired. Keep all dimensions, camera, light, materials and other component geometry unchanged. This is a targeted cable-continuity correction, not a new composition.

## Current parts: MOSFET module and ceramic K-type probe

Requested 15 October 2026: align every current parts description with the
MOSFET build and make the K-type thermocouple visibly ceramic-sheathed.
The parts illustration now contains nine labeled groups: Pi, SD card/reader,
USB supply, MAX31855, long white ceramic-sheathed K-type probe, jumper leads,
insulating nylon spacers, MOSFET module and 10 kΩ pull-down resistor.
The enclosure and SSR/heatsink remain in the separate assembly illustration.

The approved imagegen API/CLI fallback used `gpt-image-2`, medium quality and
1536 × 1024 output. Input 1 was the previous unannotated parts layout; input 2
was a crop of the MOSFET module from the earlier generated component base.
Number markers and the resistor's value label were added locally. The final
JPEG replaces `raspberry-pi-parts-generated.jpg`; the base and annotated PNG
are retained in workspace output. The original metal-probe prompt above is
superseded history, not a description of the current asset. The illustration
does not establish an exact part number, temperature rating or insulation test.

### Parts replacement prompt

Use case: precise-object-edit.
Asset type: photographic-style parts overview for the current Raspberry Pi kiln-controller build guide.
Image 1 is the edit target: the existing clean parts flat lay on a warm off-white surface. Image 2 is a component reference ONLY for the blue MOSFET trigger switch module's appearance. Keep the same restrained natural product-photo style, realistic shadows and overhead view. Recompose the flat lay as needed so every item stays separate and clearly identifiable.

Update the parts to match the current build. Show exactly these NINE numbered categories of loose, unconnected parts, without actually printing any numbers or captions (those will be added afterward):
1. One recognizable Raspberry Pi 4 board, with 40-pin header, USB-C, two micro-HDMI sockets, audio socket, Ethernet and USB ports as in Image 1.
2. One microSD card and one USB card reader placed together.
3. One black USB-C Raspberry Pi power adapter and its coiled cable, as in Image 1; this is the only power supply.
4. One small blue MAX31855 converter module with exactly TWO green thermocouple screw terminals and accessible signal-header contacts, as in Image 1.
5. One visibly CERAMIC-SHEATHED K-type kiln thermocouple: a long slender smooth WHITE ceramic protection tube with a closed tip, metal transition ferrule at the other end, and attached silver braided extension lead ending in two separate insulated conductors. It should resemble a ceramic kiln thermocouple, not a short exposed metal temperature bolt, not a thermistor, not a clear tube and not a screwdriver. Arrange the long white probe along the lower part of the image with its cable in a loose coil so the entire probe is easy to see. Replace the existing short metal probe completely; there must be only ONE thermocouple.
6. A small group of color-coded insulated jumper leads with fitted connector housings, as in Image 1.
7. Four short INSULATING nylon mounting standoffs (replace the brass standoffs in Image 1).
8. One blue MOSFET Field-Effect Transistor Trigger Switch Drive Module PWM resembling Image 2: two FLAT black MOSFET packages, a two-position DC+/DC- power terminal, a separate two-position TRIG/GND signal header and two-position OUT+/OUT- output terminal. Exactly six separate connection positions. It must not look like a cube mechanical relay. No COM/NO/NC labels.
9. One small axial 10 kΩ resistor with brown-black-orange-gold bands and short straight leads, lying separately close to the MOSFET board but not connected.

Give the MOSFET and sensor enough breathing room to distinguish them. Keep everything at plausible relative scale with generous neutral gaps for the later numbered markers. Small components may be arranged for recognition, but do not enlarge the resistor to the size of a board. There is no enclosure or SSR in this flat lay; those are shown in the separate assembled-box image. Do not add extra circuit boards, tools, relay cubes, loose power modules, batteries, certification marks, current ratings, text, captions, symbols or connections. Keep the two original blue/green board categories distinct and include the new blue MOSFET as the third circuit board beside the Pi and sensor.
