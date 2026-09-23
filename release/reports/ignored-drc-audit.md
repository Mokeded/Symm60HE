# Ignored DRC audit

Every rule configured as `ignore` in the released KiCad projects was
temporarily changed to `warning`; the released project settings were not modified.

## Symm60HE-Left

Re-enabled rules: annular_width, courtyards_overlap, footprint_filters_mismatch, footprint_type_mismatch, malformed_courtyard, mirrored_text_on_front_layer, missing_courtyard, nonmirrored_text_on_back_layer, npth_inside_courtyard, pth_inside_courtyard, silk_edge_clearance, silk_over_copper, silk_overlap, text_height, text_thickness, tuning_profile_track_geometries

| Rule | Findings |
|---|---:|
| `courtyards_overlap` | 6 |
| `missing_courtyard` | 2 |
| `npth_inside_courtyard` | 2 |
| `silk_over_copper` | 87 |
| `silk_overlap` | 19 |

## Symm60HE-Right

Re-enabled rules: annular_width, courtyards_overlap, footprint_filters_mismatch, footprint_type_mismatch, malformed_courtyard, mirrored_text_on_front_layer, missing_courtyard, nonmirrored_text_on_back_layer, npth_inside_courtyard, pth_inside_courtyard, silk_edge_clearance, silk_over_copper, silk_overlap, text_height, text_thickness, tuning_profile_track_geometries

| Rule | Findings |
|---|---:|
| `courtyards_overlap` | 6 |
| `missing_courtyard` | 3 |
| `npth_inside_courtyard` | 6 |
| `silk_edge_clearance` | 1 |
| `silk_over_copper` | 96 |
| `silk_overlap` | 22 |

## Symm60HE-Daughterboard

Re-enabled rules: annular_width, courtyards_overlap, footprint_filters_mismatch, footprint_type_mismatch, malformed_courtyard, mirrored_text_on_front_layer, missing_courtyard, nonmirrored_text_on_back_layer, npth_inside_courtyard, pth_inside_courtyard, silk_edge_clearance, silk_over_copper, silk_overlap, text_height, text_thickness, tuning_profile_track_geometries

| Rule | Findings |
|---|---:|
| `courtyards_overlap` | 9 |
| `footprint_type_mismatch` | 1 |
| `silk_edge_clearance` | 1 |
| `silk_over_copper` | 23 |

## Interpretation

The raw reports above are the authority for each location. Only findings
from rules that were ignored in the released projects are counted here.
The courtyard and footprint-type findings are metadata or documentation
issues. Silkscreen conflicts are clipped to solder-mask openings by
`tools/releases/release.py`. Physical copper, drill and routed-slot rules are enabled
in the released projects and are therefore not part of this ignored-rule
inventory. The raw reports remain the authority for every location.

| Rule | Total |
|---|---:|
| `courtyards_overlap` | 21 |
| `footprint_type_mismatch` | 1 |
| `missing_courtyard` | 5 |
| `npth_inside_courtyard` | 8 |
| `silk_edge_clearance` | 2 |
| `silk_over_copper` | 206 |
| `silk_overlap` | 41 |
