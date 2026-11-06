"""Stand-alone Vaisala WXT530-series weather transmitter -> instruments/METWXT/METWXT.blend
(collection INST_METWXT).   blender -b --factory-startup --python tools/build_inst_metwxt.py

The configuration used on ARM redeployable profiling modules (R1) and the ANL guest kit
at NIU (DERECHOS Tables 1 and 3): a WXT530-series head on a ~2 m, 60 mm galvanised pole
with a folding tripod base, a fibreglass logger/comms enclosure and a ground rod.
The WXT head itself is a copy of the wxt530 sub-assembly of instruments/MET/MET.blend
(read only), so both assets show the same sensor.
"""
import bpy, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instlib as L

NAME = 'METWXT'
coll, root = L.start(NAME)
H = 2.00                              # top of the pole; WXT mount sits on it

# ---- WXT head copied from the MET tower asset
src = os.path.join(L.REPO, 'instruments/MET/MET.blend')
with bpy.data.libraries.load(src, link=False) as (s, d):
    d.objects = [n for n in s.objects if n.startswith('wxt530')]
objs = {o.name: o for o in d.objects}
old = objs.pop('wxt530')
head = L.empty('wxt', coll, root, (0, 0, 0), 0.15)
for o in objs.values():
    coll.objects.link(o)
    o.parent = head                        # keeps local transform relative to the head
bpy.data.objects.remove(old)
# find the bottom of the head in its own frame and sit it on the pole top
zmin = min((o.matrix_parent_inverse @ o.matrix_basis @ Vector(c)).z for o in objs.values() for c in o.bound_box)
head.location = (0, 0, H - zmin)
for o in objs.values():
    o.name = o.name.replace('wxt530', 'wxt')


def build_mast(mb):
    mb.cyl((0, 0, 0.0), (0, 0, H), 0.0302, 'galvanized', seg=24)
    mb.cyl((0, 0, H - 0.004), (0, 0, H), 0.031, 'black_plastic', seg=24)
    mb.cyl((0, 0, 0.0), (0, 0, 0.012), 0.08, 'galvanized', seg=24)
    # folding tripod: collar at 0.9 m, three legs to foot plates, ground stakes
    mb.cyl((0, 0, 0.86), (0, 0, 0.94), 0.042, 'galvanized', seg=20)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        foot = Vector((0.78 * math.cos(a), 0.78 * math.sin(a), 0.02))
        top = Vector((0.045 * math.cos(a), 0.045 * math.sin(a), 0.90))
        mb.cyl(top, foot, 0.016, 'galvanized', seg=10)
        mb.box(foot + Vector((0, 0, -0.012)), (0.12, 0.12, 0.008), 'galvanized')
        mb.cyl(foot + Vector((0.04 * math.cos(a), 0.04 * math.sin(a), 0.03)),
               foot + Vector((0.04 * math.cos(a), 0.04 * math.sin(a), -0.012)), 0.008, 'galvanized', seg=8)
        mid = top.lerp(foot, 0.55)
        mb.cyl(mid, Vector((0, 0, 0.35)), 0.009, 'galvanized', seg=8)   # leg brace to the pole
    mb.cyl((0, 0, 0.33), (0, 0, 0.37), 0.04, 'galvanized', seg=20)


def build_enclosure(mb):
    # 14x12x6-inch fibreglass enclosure on unistrut, door facing south (-Y)
    for z in (0.95, 1.40):
        mb.box((0, -0.045, z), (0.30, 0.04, 0.04), 'galvanized')
        mb.box((0, -0.03, z), (0.08, 0.03, 0.07), 'stainless')
    mb.box((0, -0.16, 1.175), (0.31, 0.16, 0.36), 'fiberglass_white')
    mb.box((0, -0.243, 1.175), (0.29, 0.008, 0.34), 'fiberglass_white')
    for x in (-0.14, 0.14):
        for z in (1.03, 1.32):
            mb.cyl((x, -0.247, z), (x, -0.257, z), 0.012, 'stainless', seg=10)
    mb.box((0, -0.248, 1.29), (0.10, 0.002, 0.04), 'label')
    for x in (-0.08, 0.0, 0.08):
        mb.cyl((x, -0.16, 0.995), (x, -0.16, 0.97), 0.011, 'grey_plastic', seg=10)


def build_ground(mb):
    mb.cyl((0.35, -0.25, 0.0), (0.35, -0.25, 0.10), 0.008, 'copper', seg=10)
    mb.box((0.35, -0.25, 0.08), (0.03, 0.03, 0.03), 'brass')


def build_buried(mb):
    mb.cyl((0.35, -0.25, -0.40), (0.35, -0.25, 0.0), 0.008, 'copper', seg=10)       # ground rod
    for k in range(3):                                                              # tripod stakes
        a = math.radians(90 + 120 * k)
        f = Vector((0.82 * math.cos(a), 0.82 * math.sin(a), 0.0))
        mb.cyl(f, f + Vector((0, 0, -0.30)), 0.008, 'galvanized', seg=8)


L.part('metwxt_mast', coll, root, build_mast)
L.part('metwxt_enclosure', coll, root, build_enclosure)
L.part('metwxt_ground_rod', coll, root, build_ground)
L.part('metwxt_buried', L.below(coll), root, build_buried)
L.cable('metwxt_cable_wxt', [(0.0, -0.040, H - 0.05), (0.0, -0.040, 1.7), (0.0, -0.040, 1.45),
                             (0.08, -0.10, 1.0), (0.08, -0.16, 0.97)], 0.004, coll, root)
L.cable('metwxt_cable_power', [(-0.08, -0.16, 0.97), (-0.08, -0.20, 0.6), (-0.06, -0.12, 0.2),
                               (-0.10, -0.15, 0.01), (-0.45, -0.55, 0.0), (-0.7, -0.85, 0.0)], 0.007, coll, root)
L.cable('metwxt_ground_strap', [(0.0, -0.16, 0.97), (0.05, -0.28, 0.55), (0.25, -0.30, 0.15), (0.35, -0.25, 0.09)],
        0.003, coll, root, m='copper')

L.finish(NAME, coll, root,
         'Vaisala WXT530-series weather transmitter on stand-alone pole (METWXT)',
         ['R1', 'NIU'],
         ['ARM MET handbook DOE/SC-ARM-TR-086 (metwxt class)',
          'Vaisala WXT530 series user guide M211840EN (WXT536 0.7 kg, polycarbonate shield, AISI 316 rain plate)',
          'DERECHOS white paper Table 1 (MET / METWXT at M1, S1, R1) and Table 3 (Vaisala WXT530 at NIU)',
          'WXT head geometry copied from instruments/MET/MET.blend (wxt530 sub-assembly)'],
         f'WXT head (empty "wxt") on a 60 mm galvanised pole, sensor base at {H:.2f} m (head top ~{H + 0.24:.2f} m); '
         'folding tripod with stakes, fibreglass logger/comms enclosure at 1.0-1.35 m facing -Y, '
         'ground rod (stakes and rod below grade in METWXT_BelowGrade). North mark of the WXT is +Y. Generic stand - match to the R1 module '
         'or ADM installation when its layout is fixed.')
print('ALL DONE')
