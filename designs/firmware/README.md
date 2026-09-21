# Firmware

- [Compiled firmware binary](../../firmware/build/firmware.bin)
- [Symm60HE keyboard configuration](../../firmware/libhmk/keyboards/symm60he/keyboard.json)
- [Symm60HE firmware source directory](../../firmware/libhmk/keyboards/symm60he/)
- [Clean-build report](../../release/reports/firmware-build.txt)

The universal PCB has 69 independently observed Hall positions. Four active
key masks select the physical layout at runtime:

| Profile | Active positions |
|---|---:|
| `wkl` | 60 |
| `wklarrows` | 63 |
| `wklbs2` | 59 |
| `wklbs2arrows` | 62 |

Recalibrate after changing the physical switch layout or selecting a different
profile.
