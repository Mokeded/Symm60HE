$fn=36;
color([0.05,0.22,0.10,1.0]) import("/Users/smburke/Downloads/DAI BA Testing/TEST_BA_D2M_FIXED/Symm60HE/case/fusion360/generated/DaughterboardPCB-placed.stl");
color([0.24,0.25,0.28,1.0]) import("/Users/smburke/Downloads/DAI BA Testing/TEST_BA_D2M_FIXED/Symm60HE/case/fusion360/generated/DaughterboardPCBComponents-placed.stl");
color([0.18,0.50,0.92,0.82]) intersection() {
  union() {
    import("/Users/smburke/Downloads/DAI BA Testing/TEST_BA_D2M_FIXED/Symm60HE/case/fusion360/generated/LeftRibbonCable-placed.stl");
    import("/Users/smburke/Downloads/DAI BA Testing/TEST_BA_D2M_FIXED/Symm60HE/case/fusion360/generated/RightRibbonCable-placed.stl");
  }
  translate([112,-12,0]) cube([78,45,30]);
}
