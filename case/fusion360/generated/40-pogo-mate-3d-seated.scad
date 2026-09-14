$fn=64;
color([0.82,0.60,0.18,1.0]) translate([0.0000,0.0000,0.0000]) import("/home/user/Symm60HE/case/fusion360/generated/CaseRef-LeftSpringConnector.stl");
color([0.12,0.44,0.55,1.0]) translate([-0.0000,0.0000,0.0000]) import("/home/user/Symm60HE/case/fusion360/generated/CaseRef-LeftTargetConnector.stl");
color([0.05,0.34,0.18,0.90]) translate([0.0000,0.0000,0.0000]) import("/home/user/Symm60HE/case/fusion360/generated/CaseRef-LeftSpringPCB.stl");
color([0.05,0.34,0.18,0.90]) translate([-0.0000,0.0000,0.0000]) intersection() {
  import("/home/user/Symm60HE/case/fusion360/generated/CaseRef-LeftPCB.stl");
  translate([144.9949,56.2860,4.7072]) cube([11.0,24.200000000000003,11.0], center=true);
}
