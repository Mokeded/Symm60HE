# Switch and keycap reference-model provenance

The active Fusion handoff uses two auditable mechanical references:

- `gmk-cyl/Cherry-MX-keycaps.step` is the unmodified MIT-licensed thin-wall
  Cherry-profile CAD from Constantino Schillebeeckx, revision
  `2fa89ef205e4b1529d82fd33cef4e46f057760b1`. The exporter selects the real
  R1-R4 and 1u/1.5u/1.75u/2.25u bodies and applies only rigid placement
  transforms. GMK confirms that CYL is the original Cherry profile, uses a
  1.5 mm double-shot ABS wall and an MX-cross mount, but does not publish its
  proprietary mold CAD. These bodies are therefore dimensionally
  representative GMK CYL references, not vendor-certified GMK mold surfaces.
- `gateron-ks20-magnetic-jade/GATERON-Magnetic-Jade-KS20-specification.pdf`
  is Gateron's official specification for `KS-20TF10B045NW-Y89`. The switch
  exterior in `tools/cad/export_fusion_reference.py` is reconstructed from drawing
  `DS-02-001-A0`, including its housing, plate clips, MX cross and two locating
  pins. Gateron does not publish a production STEP for this switch.

Sources:

- https://github.com/ConstantinoSchillebeeckx/cherry-mx-keycaps
- https://www.gmk.net/en/products/keycaps-keyboards-accessories/cyl-keycaps
- https://www.gateron.com/u_file/2406/28/file/GATERONMagneticJadeSwitch-KS-20TF10B045NW-Y89.pdf

The generated `switch-keycap-model-provenance.json` stores the source hashes,
dimensions, model counts, row/width selections and measured inter-keycap
clearance for every regenerated assembly.
