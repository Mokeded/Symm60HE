# Exact vendor STEP drop-ins

This directory is reserved for manufacturer or verified-supplier CAD matching
the exact ordered MPN. Do not substitute a visually similar contact count or a
community model under these names.

The two pending files are:

- `Mill-Max_854-22-012-30-004101.step`
- `Mill-Max_856-10-012-30-051000.step`

Mill-Max publishes its configurable connector families through its verified
3D ContentCentral supplier catalog. That portal requires a free account before
STEP download, so the repository does not pretend that the generated fallback
is vendor CAD. Download the 12-position AP214/AP203 configuration for each
exact MPN, place it here, and record its SHA-256 in `../model-provenance.json`.

Keep the downloaded free-height 854 file untouched. A seated assembly needs a
separate derived working-position representation; the current 6.0 mm stack is
0.426 mm below the published initial height and retains 0.590 mm before the
published maximum compression point.
