// ============================================================
// iPad Mini E-Paper Reader — Case Design
// OpenSCAD Parametric Model
// ============================================================

// --- GLOBAL SETTINGS ---
$fn = 60;

// --- iPAD MINI 6 DIMENSIONS (mockup) ---
ipad_w = 134.8;       // width (short edge, portrait)
ipad_h = 195.4;       // height (long edge, portrait)
ipad_t = 6.3;         // thickness
ipad_corner_r = 8.5;  // corner radius

// Camera module (back, top-right when looking at back in portrait)
cam_from_top = 9.5;     // center distance from top edge
cam_from_right = 9.5;   // center distance from right edge
cam_lens_d = 10;         // lens diameter
cam_bump_d = 16;         // bump ring diameter
cam_bump_h = 1.2;        // bump protrusion

// --- E-PAPER DISPLAY ---
epd_w = 98;            // active width
epd_h = 163;           // active height
epd_t = 1.2;           // panel thickness
epd_bezel = 2;         // inactive border around active area
epd_total_w = epd_w + epd_bezel * 2;
epd_total_h = epd_h + epd_bezel * 2;

// --- PCB (represented as block) ---
pcb_w = 25;
pcb_h = 90;
pcb_t = 1.0;

// --- USB-C CUTOUT ---
usbc_w = 9.0;
usbc_h = 3.2;
usbc_r = 1.4;

// --- BATTERY (under display) ---
bat_w = 80;
bat_h = 50;
bat_t = 3.0;

// --- CASE PARAMETERS ---
case_wall = 1.5;          // wall thickness
case_corner_r = 3;        // case corner radius
bezel_angle = 35;         // angle of bezel slope around display
bezel_width = 5;          // width of angled bezel surface
case_bottom_t = 1.0;      // bottom plate thickness
case_top_shell_t = 1.2;   // top shell wall thickness

// Case internal envelope
case_content_t = epd_t + bat_t + pcb_t + 0.5; // total internal height

// Case outer dimensions (covers display + pcb area)
case_w = epd_total_w + pcb_w + 8 + case_wall * 2;  // display + gap + pcb + walls
case_h = epd_total_h + case_wall * 2;
case_t = case_bottom_t + case_content_t + case_top_shell_t;

// Position of case on iPad back (left side, centered vertically)
case_x_on_ipad = 5;   // from left edge of iPad back
case_y_on_ipad = (ipad_h - case_h) / 2;

// FPC gap between display and PCB
fpc_gap = 5;

// Display position inside case (from case origin)
epd_x = case_wall + bezel_width;
epd_y = case_wall + bezel_width;

// PCB position inside case
pcb_x = epd_x + epd_total_w + fpc_gap;
pcb_y = case_wall + (case_h - 2 * case_wall - pcb_h) / 2;

// --- SCREW PARAMETERS ---
screw_d = 2.0;           // M2 screws
screw_head_d = 3.8;
screw_head_h = 1.2;
screw_boss_d = 5.0;
screw_boss_h = case_content_t;

// Screw positions (relative to case origin)
screw_positions = [
    [case_wall + 3, case_wall + 3],
    [case_w - case_wall - 3, case_wall + 3],
    [case_wall + 3, case_h - case_wall - 3],
    [case_w - case_wall - 3, case_h - case_wall - 3],
    [case_w / 2, case_wall + 3],
    [case_w / 2, case_h - case_wall - 3],
];

// --- MAGSAFE MAGNETS ---
mag_d = 5;      // magnet diameter
mag_h = 1.5;    // magnet height
// Magnet positions (relative to case origin) — matching iPad Smart Folio magnet pattern
mag_positions = [
    // Top edge
    [case_w * 0.25, case_h - case_wall/2],
    [case_w * 0.50, case_h - case_wall/2],
    [case_w * 0.75, case_h - case_wall/2],
    // Bottom edge
    [case_w * 0.25, case_wall/2],
    [case_w * 0.50, case_wall/2],
    [case_w * 0.75, case_wall/2],
    // Left edge
    [case_wall/2, case_h * 0.33],
    [case_wall/2, case_h * 0.66],
    // Right edge
    [case_w - case_wall/2, case_h * 0.33],
    [case_w - case_wall/2, case_h * 0.66],
];

// Camera cutout in case (position relative to case origin)
// Camera is at top-right of iPad back; case is positioned at case_x_on_ipad, case_y_on_ipad
cam_cutout_x = (ipad_w - cam_from_right) - case_x_on_ipad;
cam_cutout_y = (ipad_h - cam_from_top) - case_y_on_ipad;
cam_cutout_d = cam_bump_d + 6;  // generous clearance around camera bump

// USB-C position (top of PCB strip, opening on top edge of case... 
// but actually USB is near camera = top of case)
usbc_x = pcb_x + pcb_w / 2;
usbc_z = case_bottom_t + pcb_t / 2;


// ============================================================
// MODULES
// ============================================================

// --- Rounded rectangle (2D) ---
module rounded_rect_2d(w, h, r) {
    offset(r) offset(-r) square([w, h]);
}

// --- Rounded box (3D) ---
module rounded_box(w, h, t, r) {
    linear_extrude(t)
        rounded_rect_2d(w, h, r);
}

// --- iPad Mini mockup ---
module ipad_mini() {
    color("DimGray", 0.3) {
        // Body
        difference() {
            rounded_box(ipad_w, ipad_h, ipad_t, ipad_corner_r);
            
            // Screen depression hint (front side, z=0)
            translate([3, 3, -0.1])
                rounded_box(ipad_w - 6, ipad_h - 6, 0.5, ipad_corner_r - 2);
        }
        
        // Camera bump (on back = top surface, z = ipad_t)
        translate([ipad_w - cam_from_right, ipad_h - cam_from_top, ipad_t])
            cylinder(d=cam_bump_d, h=cam_bump_h);
    }
    
    // Camera lens (dark)
    color("Black", 0.5)
        translate([ipad_w - cam_from_right, ipad_h - cam_from_top, ipad_t + cam_bump_h - 0.1])
            cylinder(d=cam_lens_d, h=0.2);
}

// --- Electronics block (simplified) ---
module electronics_block() {
    // PCB
    color("DarkGreen", 0.7)
        translate([pcb_x, pcb_y, case_bottom_t])
            cube([pcb_w, pcb_h, pcb_t]);
    
    // ESP32 module on PCB (visual hint)
    color("Silver", 0.6)
        translate([pcb_x + 3, pcb_y + pcb_h - 25, case_bottom_t + pcb_t])
            cube([18, 13, 2.4]);
    
    // USB-C connector (sticks out from top edge of case)
    color("Silver", 0.8)
        translate([usbc_x - usbc_w/2, case_h - 2, case_bottom_t])
            cube([usbc_w, 6, usbc_h]);
}

// --- E-paper display ---
module epaper_display() {
    // Panel (glass)
    color("LightGray", 0.5)
        translate([epd_x, epd_y, case_bottom_t + bat_t + 0.3])
            cube([epd_total_w, epd_total_h, epd_t]);
    
    // Active area (darker)
    color("GhostWhite", 0.9)
        translate([epd_x + epd_bezel, epd_y + epd_bezel, 
                   case_bottom_t + bat_t + 0.3 + epd_t - 0.1])
            cube([epd_w, epd_h, 0.2]);
    
    // FPC flex cable hint
    color("Orange", 0.4)
        translate([epd_x + epd_total_w, epd_y + epd_total_h/2 - 10, 
                   case_bottom_t + bat_t])
            cube([fpc_gap + 2, 20, 0.3]);
}

// --- Battery pouch ---
module battery() {
    color("SteelBlue", 0.4)
        translate([epd_x + (epd_total_w - bat_w)/2, 
                   epd_y + (epd_total_h - bat_h)/2, 
                   case_bottom_t + 0.2])
            cube([bat_w, bat_h, bat_t]);
}

// --- USB-C shaped hole (rounded rectangle) ---
module usbc_hole() {
    hull() {
        translate([usbc_r, 0, usbc_r])
            rotate([-90, 0, 0]) cylinder(r=usbc_r, h=case_wall + 4);
        translate([usbc_w - usbc_r, 0, usbc_r])
            rotate([-90, 0, 0]) cylinder(r=usbc_r, h=case_wall + 4);
        translate([usbc_r, 0, usbc_h - usbc_r])
            rotate([-90, 0, 0]) cylinder(r=usbc_r, h=case_wall + 4);
        translate([usbc_w - usbc_r, 0, usbc_h - usbc_r])
            rotate([-90, 0, 0]) cylinder(r=usbc_r, h=case_wall + 4);
    }
}

// --- Angled bezel around display window ---
module display_window_with_bezel() {
    bz = bezel_width;
    // Outer rectangle of bezel
    ox = epd_x - bz;
    oy = epd_y - bz;
    ow = epd_total_w + bz * 2;
    oh = epd_total_h + bz * 2;
    
    // Inner rectangle (display opening)
    ix = epd_x + 0.5;  // small lip to hold display
    iy = epd_y + 0.5;
    iw = epd_total_w - 1;
    ih = epd_total_h - 1;
    
    top_z = case_t;
    drop = bz * tan(bezel_angle);
    inner_z = top_z - drop;
    
    // The bezel is a sloped surface from outer edge (top_z) down to inner edge (inner_z)
    // We'll create this as a hull between outer frame at top and inner frame lower
    
    // Using polyhedron approach — or simpler: cut with angled planes
    // Simpler approach: create the shell and then cut the angle
    
    // Angled cut volume
    translate([ox, oy, inner_z])
        linear_extrude(height = drop + 1, scale = [iw/ow, ih/oh])
            translate([(ow - ow)/2, (oh - oh)/2])
                square([ow, oh]);
}

// --- Top shell ---
module top_shell() {
    bz = bezel_width;
    lip = 1.0; // lip to hold display
    
    difference() {
        // Outer shell
        rounded_box(case_w, case_h, case_t, case_corner_r);
        
        // Hollow interior (leaving walls and top)
        translate([case_wall, case_wall, case_bottom_t])
            rounded_box(case_w - case_wall*2, case_h - case_wall*2, 
                        case_t, max(0.5, case_corner_r - case_wall));
        
        // Display window opening (with small lip)
        translate([epd_x + lip, epd_y + lip, case_t - case_top_shell_t - 0.1])
            cube([epd_total_w - lip*2, epd_total_h - lip*2, case_top_shell_t + 0.2]);
        
        // Angled bezel cut — chamfer around display window
        translate([0, 0, 0]) {
            // Cut from each side with angled planes
            bevel_h = bz * tan(bezel_angle);
            
            // Top side bevel
            translate([epd_x - bz, epd_y + epd_total_h, case_t - bevel_h])
                rotate([bezel_angle, 0, 0])
                    cube([epd_total_w + bz*2, bz * 2, bz * 2]);
            
            // Bottom side bevel
            translate([epd_x - bz, epd_y - bz*2, case_t - bevel_h])
                translate([0, bz*2, 0])
                    rotate([-bezel_angle, 0, 0])
                        translate([0, -bz*2, 0])
                            cube([epd_total_w + bz*2, bz * 2, bz * 2]);
            
            // Left side bevel
            translate([epd_x - bz*2, epd_y - bz, case_t - bevel_h])
                translate([bz*2, 0, 0])
                    rotate([0, -bezel_angle, 0])
                        translate([-bz*2, 0, 0])
                            cube([bz * 2, epd_total_h + bz*2, bz * 2]);
            
            // Right side bevel
            translate([epd_x + epd_total_w, epd_y - bz, case_t - bevel_h])
                rotate([0, bezel_angle, 0])
                    cube([bz * 2, epd_total_h + bz*2, bz * 2]);
        }
        
        // Camera cutout (through entire case)
        translate([cam_cutout_x, cam_cutout_y, -1])
            cylinder(d=cam_cutout_d, h=case_t + 2);
        
        // USB-C cutout (top edge)
        translate([usbc_x - usbc_w/2, case_h - case_wall - 1, case_bottom_t])
            usbc_hole();
        
        // Screw holes through top shell into bosses
        for (pos = screw_positions) {
            translate([pos[0], pos[1], -0.1])
                cylinder(d=screw_d, h=case_t + 0.2);
        }
        
        // Magnet recesses (on bottom face of case = face against iPad)
        for (pos = mag_positions) {
            translate([pos[0], pos[1], -0.1])
                cylinder(d=mag_d + 0.2, h=mag_h + 0.1);
        }
    }
    
    // Screw bosses (inside, rising from bottom of interior)
    for (pos = screw_positions) {
        translate([pos[0], pos[1], case_bottom_t])
            difference() {
                cylinder(d=screw_boss_d, h=screw_boss_h);
                translate([0, 0, -0.1])
                    cylinder(d=screw_d, h=screw_boss_h + 0.2);
            }
    }
}

// --- Bottom plate ---
module bottom_plate() {
    difference() {
        rounded_box(case_w, case_h, case_bottom_t, case_corner_r);
        
        // Screw countersinks
        for (pos = screw_positions) {
            // Through hole
            translate([pos[0], pos[1], -0.1])
                cylinder(d=screw_d + 0.3, h=case_bottom_t + 0.2);
            // Countersink
            translate([pos[0], pos[1], -0.1])
                cylinder(d=screw_head_d, h=screw_head_h + 0.1);
        }
        
        // Camera cutout (matching top shell)
        translate([cam_cutout_x, cam_cutout_y, -1])
            cylinder(d=cam_cutout_d, h=case_bottom_t + 2);
    }
}

// --- Magnet inserts visualization ---
module magnets() {
    for (pos = mag_positions) {
        color("Silver", 0.8)
            translate([pos[0], pos[1], 0])
                cylinder(d=mag_d, h=mag_h);
    }
}

// ============================================================
// ASSEMBLY
// ============================================================

// Exploded view offset
explode = 0;  // set to 15-20 for exploded view

// iPad (reference, at z=0, case sits on top of it)
translate([case_x_on_ipad, case_y_on_ipad, -ipad_t - 2 - explode])
    ipad_mini();

// Case assembly (sits above iPad back)
translate([case_x_on_ipad, case_y_on_ipad, 0]) {
    
    // Bottom plate (against iPad)
    color("DarkSlateGray", 0.6)
    translate([0, 0, -case_bottom_t - explode * 0.5])
        bottom_plate();
    
    // Magnets
    translate([0, 0, -explode * 0.3])
        magnets();
    
    // Top shell (main body)
    color("SlateGray", 0.5)
        top_shell();
    
    // Internal components (for visualization)
    translate([0, 0, explode * 0.2]) {
        battery();
        epaper_display();
        electronics_block();
    }
}

// ============================================================
// PRINT LAYOUT (uncomment to see parts flat for printing)
// ============================================================
/*
// Top shell for printing (flipped)
translate([0, -case_h - 20, case_t])
    rotate([180, 0, 0])
        top_shell();

// Bottom plate for printing
translate([case_w + 20, -case_h - 20, 0])
    bottom_plate();
*/
