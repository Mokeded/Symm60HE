"""Shared mechanical coordinates used by PCB and plate generators."""

# These independently optimized patterns keep the complete 4 mm OD nylon
# standoff body clear of every supported switch/stabilizer opening and the
# populated/routed areas of its corresponding PCB half.  The reference names
# are stable identifiers only; mechanical alignment is defined by coordinates.
# The four points on each half form a wide support polygon instead of clustering
# near the centre seam.  Every point is on solid PCB and plate material, clears
# the union of all supported switch/stabilizer openings, and retains at least
# 1.0 mm of drill-to-copper clearance across the universal and fixed boards.
PCB_MOUNT_REFS = {
    "Left": {
        "MHL1": (28.000, 22.000),
        "MHL2": (38.000, 66.000),
        "MHL3": (137.000, 50.000),
        "MHL4": (100.000, 92.000),
    },
    "Right": {
        "MHR1": (167.000, 49.000),
        "MHR2": (204.000, 92.000),
        "MHR3": (273.000, 21.000),
        "MHR4": (299.000, 44.000),
    },
}

PLATE_STANDOFFS = {
    "L": tuple(PCB_MOUNT_REFS["Left"].values()),
    "R": tuple(PCB_MOUNT_REFS["Right"].values()),
}
