# Symm60HE libhmk target

Generated from the PCB channel map by `tools/generators/mkfirmware.py`.
Supports rapid trigger, adjustable actuation, SOCD/advanced-key bindings, four
profiles, calibration, and the dedicated Symm60HE web configurator. The four
profiles are fixed to WKL/split Backspace, Arrows/split Backspace, WKL/2U
Backspace, and Arrows/2U Backspace respectively. Inactive Hall channels are
masked in firmware and are not calibrated or processed.

Firmware v1.9 also drives the two SK6812MINI-E chains independently on PC0
(31 LEDs, left half) and PC9 (34 LEDs, right half). It provides solid,
breathing, rainbow, and wave effects; persistent brightness, speed, color, and
split-mirroring settings; and an aggregate 350 mA software current limit. RGB
defaults to off after a clean configuration reset. TMR2 and DMA2 generate both
LED data streams in parallel without blocking the Hall matrix scan or USB
interrupts.
