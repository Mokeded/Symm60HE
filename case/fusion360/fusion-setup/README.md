# Fusion 360 in-case reference setup

`Symm60HECaseSetup/` creates a fresh Fusion design around the complete
Neo-style pogo assembly. Install the folder under Fusion's API `Scripts`
directory, press **Shift+S**, select `Symm60HECaseSetup`, and click **Run**.

The script imports globally positioned component STEP files into a native
Fusion component tree and grounds that reference tree. The exact HRO USB-C
solid is included as its own component STEP with the checked J1 rotation and
world position baked directly into the B-rep geometry. Fusion therefore does
not apply any placement transform to the vendor model and cannot shift it via
the vendor STEP's unusual internal origin. All mechanical positioning is
already resolved in the component references:

- each 1.2 mm Hall PCB is aligned below its matching split gasket plate;
- Hall-sensor, capacitor and mux package bodies are imported with each Hall PCB;
- XVX Whisper EC/HE clearance switches and row-specific Cherry-profile
  keycaps occupy their assembled plate positions;
- left and right stacks have mirrored 3 degree tenting and a 7 degree typing
  angle;
- Mill-Max target connectors are directly mounted under the Hall PCBs;
- the two 20 x 6 mm floating spring PCBs and their exact Mill-Max 854 spring
  blocks are mated to the exact 856 targets at a checked 5.0 mm board-surface
  separation, with 0.2578 mm preload and 0.7582 mm remaining spring travel;
- all four ZIF bodies use the exact BOOMELE 1.0-12P / LCSC C20111 distributor
  STEP envelope rather than the former simplified boxes;
- the controller carries its fitted package bodies and exact C318884 reset/boot
  button bodies as a separately hideable reference;
- the controller is flat and left-to-right beneath the centre blocker, with
  the HRO USB-C mating mouth and its plug keepout aimed through the rear case
  wall (the vendor model direction is checked independently of J1's footprint
  angle); and
- flexible FPC solids show route and bend-clearance envelopes between each
  floating head and the controller.

The nonphysical USB-plug, pogo-travel and FPC clearance envelopes are retained
under `Cable and movement keepouts` but are hidden when the design first opens.
Turn that component on only while designing the surrounding clearances; the
rectangular USB envelope is not a manufactured part.

The design created by the current script is named
`Symm60HE Case - Componentized v6 exact vendor pogo`. The exact configured
12-position Mill-Max models and their source hashes are documented in
`../models/model-provenance.json`.

The script creates empty `Left top`, `Left bottom`, `Right top`, `Right bottom`
and `Centre blocker and controller housing` components. Build the case only in
those components and leave the grounded reference untouched.

The default Windows path is
`E:\Symm60HE-GitHub-Upload\Symm60HE\case\fusion360`. Change `REFERENCE_DIR`
near the top of the Python script if the repository is elsewhere.
