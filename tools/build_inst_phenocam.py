"""PhenoCam-style land-surface camera mast -> instruments/PHENOCAM/PHENOCAM.blend
(collection INST_PHENOCAM).   blender -b --factory-startup --python tools/build_inst_phenocam.py

DERECHOS AI thrust 4 (computer vision for land-surface state: crop stage, canopy,
residue, snow, standing water) is built on site cameras/phenocams, which the white-paper
errata note Table 1 does not trace. This is the PhenoCam Network configuration: a StarDot
NetCam SC 5MP in its weatherproof housing with sun shield (the network's supported
camera, phenocam.nau.edu FAQ), pointed north (+Y) so the canopy is front-lit and the
image is dominated by the vegetation, tilted ~20 deg below the horizon, above a row-crop
canopy that reaches ~3 m (corn) - hence a 5 m guyed mast.
Housing dimensions and mast are generic.
"""
import bpy, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instlib as L

NAME = 'PHENOCAM'
coll, root = L.start(NAME)
H = 5.0                     # mast top
ARM = 0.45                  # side arm towards +Y (view direction)
TILT = math.radians(20)     # below horizon
CAM = Vector((0, ARM, H + 0.01))      # housing sits on the arm via the tilt mount
# camera frame: local +Y = boresight, tilted down by TILT about X
M = Matrix.Translation(CAM) @ Matrix.Rotation(-TILT, 4, 'X')
R3 = M.to_3x3()


def lp(x, y, z):
    return M @ Vector((x, y, z))


def build_mast(mb):
    mb.box((0, 0, 0.03), (0.7, 0.7, 0.06), 'concrete')
    mb.box((0, 0, 0.07), (0.25, 0.25, 0.015), 'galvanized')
    mb.cyl((0, 0, 0.07), (0, 0, H), 0.0302, 'galvanized', seg=20)
    mb.cyl((0, 0, H), (0, 0, H + 0.01), 0.033, 'black_plastic', seg=20)
    mb.cyl((0, 0, 3.47), (0, 0, 3.53), 0.05, 'galvanized', seg=16)            # guy ring
    # side arm and tilt bracket
    mb.box((0, 0.0, H - 0.08), (0.08, 0.08, 0.10), 'galvanized')
    mb.beam(Vector((0, 0.03, H - 0.08)), Vector((0, ARM, H - 0.08)), 0.035, 0.035, 'aluminum')
    mb.box(Vector((0, ARM - 0.02, H - 0.05)), (0.06, 0.06, 0.03), 'aluminum')        # riser to the tilt mount
    # network/PoE + surge enclosure at 1.3 m, door south (-Y)
    mb.box((0, -0.12, 1.30), (0.26, 0.16, 0.31), 'fiberglass_white')
    mb.box((0, -0.203, 1.30), (0.24, 0.006, 0.29), 'fiberglass_white')
    mb.box((0, -0.207, 1.40), (0.09, 0.002, 0.035), 'label')
    for z in (1.18, 1.42):
        mb.box((0, -0.035, z), (0.18, 0.025, 0.03), 'galvanized')
    mb.cyl((0.25, 0.15, 0.0), (0.25, 0.15, 0.10), 0.008, 'copper', seg=8)


def build_camera(mb):
    # housing ~290 x 95 x 95 mm, sun shield on top overhanging the window
    mb.box(lp(0, 0, 0), (0.095, 0.29, 0.095), 'stardot_grey', rot=R3)
    mb.box(lp(0, 0.03, 0.058), (0.13, 0.36, 0.004), 'white_paint', rot=R3)
    for x in (-0.05, 0.05):
        mb.box(lp(x, 0.0, 0.053), (0.004, 0.20, 0.012), 'white_paint', rot=R3)
    mb.box(lp(0, 0.1455, 0), (0.080, 0.002, 0.080), 'glass', rot=R3)           # front window
    mb.cyl(lp(0, 0.130, 0.0), lp(0, 0.1445, 0.0), 0.017, 'lens_dark', seg=24)    # lens behind it
    mb.cyl(lp(0, -0.145, -0.02), lp(0, -0.17, -0.02), 0.009, 'black_plastic', seg=10)  # gland
    # tilt mount between bracket and housing
    mb.box(lp(0, 0.0, -0.055), (0.05, 0.08, 0.015), 'aluminum', rot=R3)


L.part('phenocam_mast', coll, root, build_mast)
L.part('phenocam_camera', coll, root, build_camera)
L.part('phenocam_buried', L.below(coll), root,
       lambda mb: mb.cyl((0.25, 0.15, -0.8), (0.25, 0.15, 0.0), 0.008, 'copper', seg=8))
cam = L.empty('phenocam_view', coll, root, tuple(lp(0, 0.15, 0)), 0.15)
cam.rotation_euler = (-TILT, 0, 0)                     # local +Y = boresight
for k, az in enumerate((30, 150, 270)):
    a = math.radians(az)
    anchor = Vector((3.0 * math.cos(a), 3.0 * math.sin(a), 0.0))
    L.part(f'phenocam_anchor_{k}', coll, root, lambda mb, p=anchor: (
        mb.cyl(p + Vector((0, 0, 0.0)), p + Vector((0, 0, 0.10)), 0.018, 'galvanized', seg=10),))
    L.wire(f'phenocam_guy_{k}', Vector((0.05 * math.cos(a), 0.05 * math.sin(a), 3.5)),
           anchor + Vector((0, 0, 0.10)), 0.0025, coll, root)
gl = lp(0, -0.17, -0.02)
L.cable('phenocam_cable_poe', [tuple(gl), tuple(gl + Vector((0, -0.05, -0.08))), (0.0, ARM - 0.15, H - 0.04),
                               (0.0, 0.04, H - 0.11), (0.0, 0.04, H - 0.6), (0.0, 0.04, 2.5),
                               (0.04, -0.06, 1.55), (0.06, -0.12, 1.145)], 0.0035, coll, root)
L.cable('phenocam_cable_power', [(-0.06, -0.12, 1.145), (-0.06, -0.15, 0.7), (-0.08, -0.12, 0.10),
                                 (-0.2, -0.45, 0.0), (-0.45, -0.8, 0.0)], 0.006, coll, root)

L.finish(NAME, coll, root,
         'PhenoCam-style land-surface / phenology camera (StarDot NetCam SC 5MP class)',
         ['M1', 'S1'],
         ['PhenoCam Network FAQ (phenocam.nau.edu): StarDot NetCam SC 5.0 IR in housing with mounting bracket; '
          'image dominated by the vegetation of interest, fixed field of view',
          'DERECHOS white paper section 4.2.4 (AI thrust 4: phenocams / site cameras) and errata (no Table 1 row)'],
         f'5 m galvanised mast on a concrete pad, guyed at 3.5 m (az 30/150/270); {ARM:.2f} m side arm to +Y '
         f'with the camera housing looking north (+Y), {math.degrees(TILT):.0f} deg below the horizon '
         '(empty phenocam_view at the window). PoE/surge enclosure at 1.3 m facing -Y. Generic mast; '
         'set the arm azimuth to the field the camera should frame.')
print('ALL DONE')
