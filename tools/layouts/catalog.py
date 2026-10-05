"""Names and physical choices for the eight current fixed-layout panels."""

# Three independent choices produce the eight manufactured combinations:
# left bottom row, right bottom row, and Backspace type.
LAYOUT_SPECS = {
    "wkl": ("wkl", "wkl", "split"),
    "wklarrows": ("three-key", "arrows", "split"),
    "wklbs2": ("wkl", "wkl", "2u"),
    "wklbs2arrows": ("three-key", "arrows", "2u"),
    "wkl-left-arrows-right": ("wkl", "arrows", "split"),
    "three-key-left-wkl-right": ("three-key", "wkl", "split"),
    "wkl-left-arrows-right-bs2": ("wkl", "arrows", "2u"),
    "three-key-left-wkl-right-bs2": ("three-key", "wkl", "2u"),
}

LAYOUTS = tuple(LAYOUT_SPECS)


def source_layout(layout, side):
    """Return the switch-map layout used by one half of a fixed pair."""
    left_bottom, right_bottom, backspace = LAYOUT_SPECS[layout]
    if side == "Left":
        return "wklarrows" if left_bottom == "three-key" else "wkl"
    suffix = "arrows" if right_bottom == "arrows" else ""
    return ("wklbs2" if backspace == "2u" else "wkl") + suffix
