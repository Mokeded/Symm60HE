# Exact vendor STEP drop-ins

This directory is reserved for manufacturer or verified-supplier CAD matching
the exact ordered MPN. Do not substitute a visually similar contact count or a
community model under these names.

The two installed exact configured files are:

- `Mill-Max_854-22-012-30-004101.step`
- `Mill-Max_856-10-012-30-051000.step`

Mill-Max publishes its configurable connector families through its verified
3D ContentCentral supplier catalog. These files were downloaded as the exact
12-position AP214 configurations. Their hashes and measured envelopes are
recorded in `../model-provenance.json`.

The source 854 STEP remains untouched. The generated seated assembly uses its
housing and pin geometry directly, splitting at the housing face and moving
only the exposed plunger ends. The 5.0 mm board separation applies 0.2578 mm
preload and leaves 0.7582 mm of the published 1.016 mm travel. The old 6.0 mm
placeholder spacing would leave a 0.7422 mm open gap with the exact models.
