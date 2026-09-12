# Symm60HE one-piece serpentine pogo prototype

This is the option-2 cable-free experiment: a single 0.8 mm, two-layer FR-4
controller daughterboard with two routed compliant arms.  The existing FFC
daughterboard and keyboard halves are unchanged.

## Electrical construction

- Each arm carries 16 explicit 0.18 mm traces on B.Cu.
- The moving spans contain no vias, footprints, or copper pours.
- Vias are confined to the rigid controller and connector landing areas.
- Each interface provides four ADC signals, the three mux-select signals,
  two `+3V3A` contacts, and seven GND contacts.
- `PSL1` and `PSR1` use Mill-Max `855-22-016-30-004101` spring connectors.
- The matching target is Mill-Max `857-10-016-30-051000`.
- The unpopulated J2/J3 copper is retained as DNP transition/test lands; it has
  no paste apertures and must not be fitted with an FFC connector.

The generated pin map is in `Symm60HE-serpentine-pogo16-pinout.csv`.

## Prototype limits

This board is for static tent-angle qualification, not repeated flexing.  Mate
and unmate it only with power removed.  Support the central controller island
and both pogo landing islands in the fixture so the routed arms absorb the
small alignment/tent displacement rather than the solder joints.

The keyboard-half target footprints are deliberately not substituted into the
production halves yet.  First qualify connector alignment, contact resistance,
continuity under the intended tent angle, USB stability, and Hall-sensor noise
with the existing spring/target coupons.  After that gate passes, integrate the
857 targets into copies of the two halves and rerun the full DRC and mechanical
stack checks.

## Regeneration and verification

```sh
./.venv/bin/python tools/make_serpentine_pogo.py
/opt/homebrew/Caskroom/kicad/10.0.5/KiCad/KiCad.app/Contents/MacOS/kicad-cli \
  pcb drc --refill-zones --save-board \
  --output pcb/variants/pogo-serpentine/Symm60HE-Serpentine-Daughterboard-drc.rpt \
  pcb/variants/pogo-serpentine/Symm60HE-Serpentine-Daughterboard.kicad_pcb
./.venv/bin/python tools/verify_serpentine_pogo.py
```
