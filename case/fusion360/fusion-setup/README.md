# Fusion 360 in-case reference setup

`Symm60HECaseSetup/` creates a fresh Fusion design around the complete
Neo-style pogo assembly. Install the folder under Fusion's API `Scripts`
directory, press **Shift+S**, select `Symm60HECaseSetup`, and click **Run**.

The script imports `Symm60HE-case-reference-assembly.step` exactly once and
grounds it. All mechanical positioning is already resolved in that STEP:

- each 1.2 mm Hall PCB is aligned below its matching split gasket plate;
- switches and keycaps occupy their assembled plate positions;
- left and right stacks have mirrored 3 degree tenting and a 7 degree typing
  angle;
- Mill-Max target connectors are directly mounted under the Hall PCBs;
- the two 20 x 6 mm floating spring PCBs and their spring blocks are mated to
  those targets at the 6 mm board-to-board datum;
- the controller is flat and left-to-right beneath the centre blocker, with
  USB-C and its plug keepout aimed through the rear case wall; and
- flexible FFC solids show route and bend-clearance envelopes between each
  floating head and the controller.

The script creates empty `Left top`, `Left bottom`, `Right top`, `Right bottom`
and `Centre blocker and controller housing` components. Build the case only in
those components and leave the grounded reference untouched.

The default Windows path is
`E:\Symm60HE-GitHub-Upload\Symm60HE\case\fusion360`. Change `REFERENCE_DIR`
near the top of the Python script if the repository is elsewhere.
