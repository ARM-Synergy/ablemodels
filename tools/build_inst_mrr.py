"""METEK MRR-PRO micro rain radar -> instruments/MRR/MRR.blend (collection INST_MRR).
blender -b --factory-startup --python tools/build_inst_mrr.py

Geometry: 24 GHz FMCW, vertically pointing offset-paraboloid antenna, 600 mm aperture
(METEK MRR-PRO datasheet 2024-07-05: offset antenna 600 mm, 40.1 dBi, 1.5 deg beam, ~20 kg).
The reflector is a true offset section of z = (x^2+y^2)/(4f) with the focus on the
paraboloid axis, so the beam leaves vertically; the transceiver/feed housing sits at the
focus on the -X side and looks down-and-across into the dish (classic MRR silhouette).
Mast, base frame and junction box are generic (no ARM installation drawing available).
"""
import bpy, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instlib as L

NAME = 'MRR'
coll, root = L.start(NAME)

F = 0.40          # focal length (m) - f/D ~ 0.67 typical of offset dishes
R = 0.30          # aperture radius (600 mm)
X0 = 0.42         # offset of the aperture centre from the paraboloid axis
ZV = 1.02         # height of the (virtual) paraboloid vertex
MAST_X = X0       # mast under the aperture centre


def dish_z(x, y):
    return ZV + (x * x + y * y) / (4 * F)


def dish_pt(rr, th, off=0.0):
    rr = max(rr, 1e-3)                     # avoid a collapsed centre ring
    xa = X0 + rr * math.cos(th)            # in paraboloid coordinates
    y = rr * math.sin(th)
    z = dish_z(xa, y)
    # surface normal of z = r^2/4f points (-x/2f, -y/2f, 1)
    n = Vector((-xa / (2 * F), -y / (2 * F), 1)).normalized()
    p = Vector((xa - MAST_X, y, z)) + n * off
    return tuple(p)


# local frame: mast at origin; paraboloid axis at x = -MAST_X
AX = -MAST_X
FOCUS = Vector((AX, 0, ZV + F))
DISH_C = Vector(dish_pt(0, 0))


def build_base(mb):
    # square galvanised ground frame with levelling feet and a 60 mm mast
    for sx in (-1, 1):
        mb.box((0, sx * 0.30, 0.03), (0.70, 0.05, 0.05), 'galvanized')
        mb.box((sx * 0.30, 0, 0.03), (0.05, 0.70, 0.05), 'galvanized')
        for sy in (-1, 1):
            mb.cyl((sx * 0.33, sy * 0.33, 0.0), (sx * 0.33, sy * 0.33, 0.06), 0.035, 'galvanized', seg=16)
            mb.cyl((sx * 0.33, sy * 0.33, 0.0), (sx * 0.33, sy * 0.33, 0.012), 0.06, 'black_plastic', seg=16)
            # diagonal braces up to the mast
            mb.cyl((sx * 0.28, sy * 0.28, 0.05), (sx * 0.03, sy * 0.03, 0.45), 0.012, 'galvanized', seg=8)
    mb.box((0, 0, 0.065), (0.16, 0.16, 0.012), 'galvanized')
    mb.cyl((0, 0, 0.07), (0, 0, ZV - 0.06), 0.0302, 'galvanized', seg=24)
    mb.cyl((0, 0, ZV - 0.06), (0, 0, ZV - 0.055), 0.034, 'galvanized', seg=24)


def build_reflector(mb):
    nr, nt = 10, 64
    front = [[dish_pt(R * i / nr, 2 * math.pi * j / nt) for j in range(nt)] for i in range(nr + 1)]
    back = [[dish_pt(R * i / nr, 2 * math.pi * j / nt, -0.012) for j in range(nt)] for i in range(nr + 1)]
    mb.grid(front, 'radar_white', close_u=True)
    mb.grid(list(reversed(back)), 'radar_white', close_u=True)
    rim = [front[-1], [dish_pt(R + 0.012, 2 * math.pi * j / nt, -0.006) for j in range(nt)], back[-1]]
    mb.grid(rim, 'radar_white', close_u=True)


def build_backframe(mb):
    # yoke on the mast top, two arms to the reflector back, ring stiffener
    top = Vector((0, 0, ZV - 0.055))
    mb.box(top + Vector((0, 0, 0.02)), (0.18, 0.12, 0.012), 'galvanized')
    for th in (math.radians(140), math.radians(220), math.radians(0)):
        p = Vector(dish_pt(0.62 * R, th, -0.02))
        mb.cyl(top + Vector((0, 0, 0.02)), p, 0.011, 'galvanized', seg=8)
        mb.box(p, (0.06, 0.06, 0.008), 'galvanized')
    ring = [dish_pt(0.62 * R, 2 * math.pi * j / 32, -0.025) for j in range(33)]
    for a, b in zip(ring, ring[1:]):
        mb.cyl(a, b, 0.008, 'aluminum', seg=6)


AXIS = (DISH_C - FOCUS).normalized()     # feed boresight
RIM_X = X0 - R - MAST_X - 0.03            # just outside the low rim of the reflector


def build_feed(mb):
    # transceiver housing behind the focus, conical horn at the focus
    h0 = FOCUS - AXIS * 0.02
    mb.cyl(h0, FOCUS + AXIS * 0.06, 0.028, 'metek_grey', r1=0.055, seg=24)      # horn
    mb.cyl(FOCUS + AXIS * 0.06, FOCUS + AXIS * 0.062, 0.050, 'black_plastic', seg=24)  # radome cap
    mb.cyl(h0 - AXIS * 0.26, h0, 0.075, 'metek_grey', seg=28)                 # transceiver body
    mb.cyl(h0 - AXIS * 0.275, h0 - AXIS * 0.26, 0.078, 'metek_grey', seg=28)
    for k in range(8):                                                          # cooling fins
        c = h0 - AXIS * (0.04 + 0.025 * k)
        mb.cyl(c, c - AXIS * 0.006, 0.083, 'aluminum', seg=28)
    mb.cyl(h0 - AXIS * 0.275, h0 - AXIS * 0.30, 0.022, 'black_plastic', seg=12)  # connector
    # feed arm: from a bracket below the reflector's low rim (outside the aperture) to a
    # clamp on the housing; a strut ties the bracket back to the mast yoke
    clamp = h0 - AXIS * 0.14
    side = Vector((0, 1, 0))
    brk = Vector((RIM_X, 0, ZV - 0.035))
    mb.box(brk, (0.05, 0.30, 0.03), 'galvanized')
    mb.cyl(Vector((0, 0, ZV - 0.035)), brk, 0.014, 'galvanized', seg=10)
    for s in (-1, 1):
        mb.cyl(brk + side * s * 0.12, clamp + side * s * 0.07, 0.012, 'galvanized', seg=8)
        mb.box(clamp + side * s * 0.075, (0.02, 0.02, 0.05), 'galvanized')
    mb.cyl(clamp - side * 0.085, clamp + side * 0.085, 0.006, 'stainless', seg=8)


def build_box(mb):
    # power / heater / network junction box on the mast
    mb.box((0, -0.135, 0.55), (0.30, 0.17, 0.40), 'grey_plastic')
    mb.box((0, -0.222, 0.55), (0.26, 0.006, 0.36), 'grey_plastic')
    mb.box((0, -0.226, 0.66), (0.12, 0.002, 0.05), 'label')
    for x in (-0.07, 0.0, 0.07):
        mb.cyl((x, -0.135, 0.35), (x, -0.135, 0.325), 0.012, 'black_plastic', seg=10)
    for z in (0.40, 0.70):
        mb.box((0, -0.04, z), (0.12, 0.03, 0.03), 'stainless')


L.part('mrr_base', coll, root, build_base)
L.part('mrr_reflector', coll, root, build_reflector)
L.part('mrr_backframe', coll, root, build_backframe)
L.part('mrr_transceiver', coll, root, build_feed)
L.part('mrr_junction_box', coll, root, build_box)
L.empty('mrr_focus', coll, root, tuple(FOCUS), 0.1)
tail = FOCUS - AXIS * 0.31
L.cable('mrr_cable_rf', [(0.0, -0.135, 0.75), (0.0, -0.10, 0.80), (0.0, -0.036, 0.86),
                         (0.0, -0.036, ZV - 0.07), (RIM_X * 0.5, -0.03, ZV - 0.06),
                         (RIM_X, -0.14, ZV - 0.02), tuple(Vector((RIM_X, -0.13, ZV)).lerp(tail, 0.5) + Vector((0, 0, -0.02))),
                         tuple(tail)], 0.008, coll, root)
L.cable('mrr_cable_power', [(-0.07, -0.135, 0.33), (-0.07, -0.16, 0.12), (-0.10, -0.22, 0.02),
                            (-0.25, -0.45, 0.0), (-0.40, -0.62, 0.0)], 0.009, coll, root)

L.finish(NAME, coll, root,
         'METEK MRR-PRO Micro Rain Radar (24 GHz FMCW, vertically pointing)',
         ['R1', 'NIU'],
         ['METEK MRR-PRO datasheet 2024-07-05: offset antenna 600 mm, 40.1 dBi, 1.5 deg 3 dB beamwidth, ~20 kg',
          'DERECHOS white paper Table 1 (MRR, R1, priority 3) and Table 3 (METEK MRR at NIU)'],
         'Offset paraboloid (D 600 mm, f 400 mm, offset 420 mm) on a 60 mm galvanised mast with a '
         'square levelling frame; transceiver/feed at the focus on the -X side, beam vertical over '
         'the aperture centre (x = 0, top of dish ~1.2 m). Mast, frame and box are generic - adjust '
         'to the as-deployed ARM/ANL mount when photos are available. Empty mrr_focus marks the feed.')
print('ALL DONE')
