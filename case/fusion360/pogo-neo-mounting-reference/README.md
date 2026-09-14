# Symm60HE Neo pogo mounting reference for Fusion 360

Open `Symm60HE-Neo-Pogo-Mounting-Reference.step` in Fusion 360. The assembly is deliberately made from separately named solids. If Fusion imports a flat body list, use the matching individual STEP files under `generated/` to create components. The exploded STEP is provided only to make the stack and retention order easier to inspect.

This is an example electronics carrier, not a finished or printable case. Build the enclosure around the green PCB references and keep the blue carrier, pale hard-stop, black Poron and cyan FPC envelopes as reserved volumes. The translucent 32 mm Hall-PCB squares are local target datums; replace them with the full left/right PCB references.

The spring and target connector bodies include all twelve contacts at 1.27 mm pitch. The translucent orange spring-travel bodies reserve the complete 4.216 mm initial-height envelope; do not build case features inside them. These are dimensioned engineering references rather than vendor-certified STEP models.

The controller is rigidly supported on a 1.2 mm floor. Two M2 fastener envelopes use its existing NPTH holes, while two compliant edge ledges prevent rocking. Do not bow the controller when tightening it. Each 20 x 20 x 1.2 mm spring PCB floats in a 20.8 mm pocket on four 0.8 mm Poron pads and is retained only at its perimeter. The direct target travels with the gasket-mounted Hall PCB. Four small optional stops protect the pogo contacts from bottoming; relocate their contact patches as needed to avoid sensors, traces and components.

The FPC solids are route/clearance examples, not formed-cable drawings. Keep a service loop, respect the flex-PCB supplier's dynamic bend guidance, and verify the final path at both gasket travel limits. Magnets are not part of this reference and remain DNP until Hall-offset/noise testing.
