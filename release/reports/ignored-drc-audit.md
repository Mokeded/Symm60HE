# Ignored DRC audit

Every rule configured as `ignore` in the released KiCad projects was
temporarily changed to `warning`; the released project settings were not modified.

## Symm60HE-Left

Re-enabled rules: annular_width, courtyards_overlap, footprint_filters_mismatch, footprint_type_mismatch, hole_clearance, hole_to_hole, malformed_courtyard, mirrored_text_on_front_layer, missing_courtyard, nonmirrored_text_on_back_layer, npth_inside_courtyard, pth_inside_courtyard, silk_edge_clearance, silk_over_copper, silk_overlap, text_height, text_thickness, track_not_centered_on_via, tuning_profile_track_geometries

| Rule | Findings |
|---|---:|
| `missing_courtyard` | 6 |
| `nonmirrored_text_on_back_layer` | 199 |
| `silk_over_copper` | 68 |

## Symm60HE-Right

Re-enabled rules: annular_width, courtyards_overlap, footprint_filters_mismatch, footprint_type_mismatch, hole_clearance, hole_to_hole, malformed_courtyard, mirrored_text_on_front_layer, missing_courtyard, nonmirrored_text_on_back_layer, npth_inside_courtyard, pth_inside_courtyard, silk_edge_clearance, silk_over_copper, silk_overlap, text_height, text_thickness, track_not_centered_on_via, tuning_profile_track_geometries

| Rule | Findings |
|---|---:|
| `hole_to_hole` | 1 |
| `missing_courtyard` | 5 |
| `nonmirrored_text_on_back_layer` | 199 |
| `silk_over_copper` | 70 |

## Symm60HE-Daughterboard

Re-enabled rules: annular_width, courtyards_overlap, footprint_filters_mismatch, footprint_type_mismatch, hole_clearance, hole_to_hole, malformed_courtyard, mirrored_text_on_front_layer, missing_courtyard, nonmirrored_text_on_back_layer, npth_inside_courtyard, pth_inside_courtyard, silk_edge_clearance, silk_over_copper, silk_overlap, text_height, text_thickness, track_not_centered_on_via, tuning_profile_track_geometries

| Rule | Findings |
|---|---:|
| `footprint_type_mismatch` | 1 |
| `missing_courtyard` | 6 |
| `nonmirrored_text_on_back_layer` | 42 |
| `silk_edge_clearance` | 5 |
| `silk_over_copper` | 20 |

## Interpretation

The raw reports above are the authority for each location. Only findings
from rules that were ignored in the released projects are counted here.
The courtyard, footprint-type and back-text findings are metadata or
documentation issues. Silkscreen conflicts are clipped to solder-mask
openings by `tools/release.py`. The one hole-to-hole finding is a tangent
pair of NPTH holes at HER24/SR2 on the right board: mutually exclusive
up-arrow and 2.25u-shift/stabilizer geometry on the universal PCB. It must
be confirmed in the fabricator viewer, or avoided with a layout-specific PCB.

| Rule | Total |
|---|---:|
| `footprint_type_mismatch` | 1 |
| `hole_to_hole` | 1 |
| `missing_courtyard` | 17 |
| `nonmirrored_text_on_back_layer` | 440 |
| `silk_edge_clearance` | 5 |
| `silk_over_copper` | 158 |
