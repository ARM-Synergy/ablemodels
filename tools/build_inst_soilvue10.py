"""Campbell Scientific SoilVUE10 TDR soil profile probe -> instruments/SOILVUE10/SOILVUE10.blend
(collection INST_SOILVUE10).   blender -b --factory-startup --python tools/build_inst_soilvue10.py

DERECHOS section 3.1 advocates SoilVue10 profiling as close to (ideally in) the farm fields
at M1 and S1, and ATMOS/ANL run them (white paper Table 4). Specs (Campbell SoilVUE10
spec sheet via NOAA PSL): 1 m model ~1.05 m long, 52 mm body (58 mm over the thread),
nine sensing depths 5-100 cm, installed vertically in a 5 cm augered hole with the top
flush with the soil surface.

Model: the threaded probe below grade (helix approximated by thread rings, sensing-ring
marks at each depth), its cable in a shallow trench to a small logger enclosure (CR6-class)
on a T-post with a 20 W solar panel facing south. The logger stand is generic.
"""
import bpy, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instlib as L

NAME = 'SOILVUE10'
coll, root = L.start(NAME)
LEN = 1.05
DEPTHS = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.75, 1.00]
POST = Vector((0.0, 1.5, 0.0))         # logger post 1.5 m north of the probe


def build_probe(mb):
    """Below grade: the probe body, tip, threads and sensing rings."""
    mb.cyl((0, 0, -LEN), (0, 0, -0.005), 0.026, 'black_plastic', seg=24)
    mb.cyl((0, 0, -LEN - 0.04), (0, 0, -LEN), 0.026, 'black_plastic', r1=0.004, seg=24)   # tapered tip
    z = -0.03
    while z > -LEN + 0.01:                                                                   # thread crests
        mb.cyl((0, 0, z), (0, 0, z - 0.006), 0.029, 'black_plastic', seg=24)
        z -= 0.03
    for d in DEPTHS:                                                                         # sensing rings
        mb.cyl((0, 0, -d + 0.008), (0, 0, -d - 0.008), 0.0295, 'stainless', seg=24)


def build_top(mb):
    """At the surface: flush cap, gland, tamped ring and trench scar."""
    mb.cyl((0, 0, -0.005), (0, 0, 0.004), 0.027, 'grey_plastic', seg=24)                   # top cap, flush
    mb.cyl((0, 0, 0.004), (0, 0.0, 0.03), 0.007, 'black_plastic', seg=10)                  # cable gland
    mb.cyl((0, 0, 0.0), (0, 0, 0.008), 0.12, 'soil_fresh', r1=0.07, seg=24)                # tamped ring
    mb.beam(Vector((0, 0.05, 0.002)), POST + Vector((0, -0.06, 0.002)), 0.10, 0.006, 'soil_fresh')  # trench scar


def build_logger(mb):
    p = POST
    # steel T-post driven 0.6 m, enclosure and solar panel on U-bolts
    mb.box(p + Vector((0, 0, 0.65)), (0.045, 0.012, 1.30), 'grey_paint')                  # above-ground T-post
    mb.box(p + Vector((0, 0.012, 0.65)), (0.012, 0.035, 1.30), 'grey_paint')
    mb.box(p + Vector((0, -0.10, 0.82)), (0.26, 0.15, 0.31), 'fiberglass_white')
    mb.box(p + Vector((0, -0.178, 0.82)), (0.24, 0.006, 0.29), 'fiberglass_white')
    mb.box(p + Vector((0, -0.182, 0.92)), (0.09, 0.002, 0.035), 'label')
    for z in (0.70, 0.94):
        mb.box(p + Vector((0, -0.015, z)), (0.18, 0.025, 0.03), 'galvanized')
    mb.cyl(p + Vector((0.06, -0.10, 0.665)), p + Vector((0.06, -0.10, 0.64)), 0.010, 'grey_plastic', seg=10)
    # 20 W panel tilted 45 deg to the south at the top of the post
    tilt = Matrix.Rotation(math.radians(-45), 3, 'X')
    c = p + Vector((0, -0.12, 1.33))
    mb.box(c, (0.50, 0.36, 0.03), 'aluminum', rot=tilt)
    mb.box(c + tilt @ Vector((0, 0, 0.0155)), (0.47, 0.33, 0.002), 'solar_cell', rot=tilt)
    mb.beam(p + Vector((0, -0.01, 1.25)), c + tilt @ Vector((0, 0, -0.02)), 0.03, 0.03, 'galvanized')
    mb.beam(p + Vector((0, -0.01, 1.42)), c + tilt @ Vector((0, 0.10, -0.02)), 0.025, 0.025, 'galvanized')


L.part('soilvue10_probe', L.below(coll), root, build_probe)
L.part('soilvue10_top_cap', coll, root, build_top)
L.part('soilvue10_post_driven', L.below(coll), root, lambda mb: (
    mb.box(POST + Vector((0, 0, -0.30)), (0.045, 0.012, 0.60), 'grey_paint'),
    mb.box(POST + Vector((0, 0.012, -0.30)), (0.012, 0.035, 0.60), 'grey_paint'),
    mb.box(POST + Vector((0, 0.03, -0.25)), (0.10, 0.004, 0.18), 'grey_paint')))
L.part('soilvue10_logger', coll, root, build_logger)
L.empty('soilvue10_top', coll, root, (0, 0, 0), 0.1)
L.cable('soilvue10_cable', [(0, 0, 0.02), (0, 0.06, 0.004), (0, 0.12, 0.0), (0, 0.8, 0.0),
                            tuple(POST + Vector((0.06, -0.20, 0.0))), tuple(POST + Vector((0.06, -0.12, 0.10))),
                            tuple(POST + Vector((0.06, -0.10, 0.64)))], 0.0035, coll, root)
L.cable('soilvue10_solar_lead', [tuple(POST + Vector((-0.20, -0.18, 1.22))), tuple(POST + Vector((-0.12, -0.10, 1.05))),
                                 tuple(POST + Vector((-0.08, -0.10, 0.975)))], 0.003, coll, root)

L.finish(NAME, coll, root,
         'Campbell Scientific SoilVUE10 TDR soil moisture and temperature profile probe (1 m)',
         ['M1', 'S1', 'NIU'],
         ['Campbell Scientific SoilVUE10 spec sheet (NOAA PSL copy): 1 m model ~1.05 m, 52/58 mm diameter, '
          'depths 5,10,20,30,40,50,60,75,100 cm, top flush with the surface in a 5 cm auger hole',
          'DERECHOS white paper section 3.1 (SoilVue10 advocacy at M1/S1) and Table 4 (ATMOS SoilVUE10)'],
         'Probe top flush at the origin (empty soilvue10_top), body to -1.05 m in SOILVUE10_BelowGrade with stainless marks at the '
         'nine sensing depths; cable in a shallow trench to a CR6-class enclosure on a steel T-post 1.5 m '
         'north (+Y) with a 20 W panel tilted 45 deg south. Logger stand is generic.')
print('ALL DONE')
