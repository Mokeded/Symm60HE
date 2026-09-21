# Fusion 360 Neo-style pogo reference

Import `Symm60HE-Neo-Pogo-Reference.step` into Fusion 360. The editable source
is `Symm60HE-Neo-Pogo-Reference.FCStd`; although that source is FreeCAD-native,
the STEP imports as separately named bodies and can be converted to Fusion
components.

This assembly contains 35 bodies:

- the two populated keyboard PCBs;
- the two split universal plates with side-only gasket tabs;
- both switch and keycap visualization banks;
- the flat rigid controller and its central tray;
- two spring heads floating in fixed-angle kernel apertures;
- two direct-target connector envelopes on the moving Hall PCBs;
- dimensioned Mill-Max 854/856 connector models with all twelve contacts,
  maximum-extension pogo keep-outs, 12-way FFC envelopes, hard stops, asymmetric
  perimeter keys, clamps, shims, and DNP magnet envelopes.

The connector references use the selected 12-position Mill-Max
`854-22-012-30-004101` spring and `856-10-012-30-051000` target geometry. The
contacts are shown at 1.27 mm pitch and the translucent maximum-extension
envelopes reserve the spring's full 4.216 mm initial height. Treat those
envelopes as case keep-outs. These are dimensioned engineering references, not
vendor-certified STEP models, so verify the production stack with real parts.

The controller lies lengthwise on the centreline, is flat across the lateral tent, and shares the assembly's
11 degree front-to-back typing plane. Its spring modules follow the opposing
6 degree tent planes. The direct targets travel with the Hall PCBs, while the
spring heads can follow them within their captured apertures. The plates carry
only the side gasket tabs. The model is a case-building and interference-check reference, not proof
of physical connector fit.
