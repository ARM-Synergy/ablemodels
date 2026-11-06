"""GNDRAD upwelling radiometer stand (+ downward IRT, the GNDIRT) -> instruments/GNDRAD/GNDRAD.blend
(collection INST_GNDRAD).   blender -b --factory-startup --python tools/build_inst_gndrad.py

Per the GNDRAD handbook (ARM TR-027, T. Stoffel): upwelling shortwave by an inverted
pyranometer (Eppley PSP, 2pi sr, 0.3-3 um) and upwelling longwave by an inverted
pyrgeometer (Eppley PIR, 4-50 um), both mounted inverted WITHOUT ventilation 10 m above
ground looking at the surface. DERECHOS Table 1 also requests a ground-viewing IRT
(GNDIRT), which ARM mounts on the same boom.

Model: guyed 10 m tilt-down aluminium mast on a concrete pad, 2 m boom to the south (-Y)
so the sensors view undisturbed ground away from the mast, crossarm at the boom tip with
PSP (west), IRT (centre, nadir) and PIR (east). Radiometer bodies are generic PSP/PIR-sized
(the field units may be Kipp & Zonen CMP22/CGR4); boom length and guy layout are generic.
"""
import bpy, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instlib as L

NAME = 'GNDRAD'
coll, root = L.start(NAME)
HB = 10.0          # boom height (handbook: 10 m AGL)
BOOM = 2.0         # boom length towards -Y
TIP = Vector((0, -BOOM, HB))
PLATE_C = -0.030 - 0.051   # radiometer case centre: shield top meets the plate underside


def build_mast(mb):
    mb.box((0, 0, 0.025), (0.9, 0.9, 0.05), 'concrete')
    mb.box((0, 0, 0.06), (0.36, 0.36, 0.02), 'galvanized')
    for sx in (-1, 1):                                   # tilt-down hinge cheeks
        mb.box((sx * 0.07, 0, 0.17), (0.012, 0.16, 0.20), 'galvanized')
    mb.cyl((-0.09, 0, 0.22), (0.09, 0, 0.22), 0.015, 'stainless', seg=12)
    for x in (-0.13, 0.13):
        for y in (-0.13, 0.13):
            mb.cyl((x, y, 0.07), (x, y, 0.11), 0.012, 'stainless', seg=8)
    secs = [(0.07, 4.0, 0.060), (4.0, 7.5, 0.048), (7.5, HB + 0.35, 0.038)]
    for z0, z1, r in secs:
        mb.cyl((0, 0, z0), (0, 0, z1), r, 'aluminum', seg=24)
        mb.cyl((0, 0, z1 - 0.05), (0, 0, z1 + 0.02), r + 0.008, 'aluminum', seg=24)  # splice collar
    for zg in (4.5, 9.0):                                # guy rings
        mb.cyl((0, 0, zg - 0.03), (0, 0, zg + 0.03), 0.065, 'galvanized', seg=20)
    # air terminal
    mb.cyl((0, 0, HB + 0.35), (0, 0, HB + 0.95), 0.008, 'copper', r1=0.003, seg=8)
    # boom, brace and crossarm
    mb.beam((0, -0.05, HB), TIP, 0.05, 0.05, 'aluminum')
    mb.box((0, -0.06, HB), (0.14, 0.04, 0.16), 'galvanized')            # boom clamp
    mb.cyl((0, -0.04, HB - 0.75), (0, -1.2, HB - 0.03), 0.014, 'aluminum', seg=10)
    mb.box((0, -0.05, HB - 0.75), (0.12, 0.04, 0.08), 'galvanized')
    mb.beam(TIP + Vector((-0.40, 0, 0)), TIP + Vector((0.40, 0, 0)), 0.04, 0.04, 'aluminum')
    mb.box(TIP, (0.10, 0.10, 0.07), 'galvanized')                        # crossarm clamp
    for x in (-0.28, 0.28):                                              # inverted mounting plates
        mb.box(TIP + Vector((x, 0, -0.025)), (0.15, 0.15, 0.010), 'aluminum')   # top touches the arm
    # junction box at the boom root, logger enclosure at the base (door -Y)
    mb.box((0.10, -0.10, HB - 0.35), (0.16, 0.10, 0.20), 'grey_plastic')
    mb.box((0, -0.17, 1.45), (0.40, 0.20, 0.50), 'fiberglass_white')
    mb.box((0, -0.273, 1.45), (0.38, 0.008, 0.48), 'fiberglass_white')
    mb.box((0, -0.278, 1.6), (0.12, 0.002, 0.05), 'label')
    for z in (1.25, 1.65):
        mb.box((0, -0.06, z), (0.36, 0.04, 0.04), 'galvanized')


def radiometer(mb, c, kind):
    """Inverted PSP ('sw') or PIR ('lw') body centred at c, domes pointing down (-Z)."""
    c = Vector(c)
    body_top = c + Vector((0, 0, 0.045))
    mb.cyl(body_top, body_top + Vector((0, 0, 0.006)), 0.085, 'kipp_white', seg=40)   # sun/guard shield
    mb.cyl(c, body_top, 0.064, 'kipp_white', seg=40)                                  # case
    mb.cyl(c - Vector((0, 0, 0.012)), c, 0.058, 'black_anod', seg=40)                  # base ring
    for k in range(3):                                                                # levelling screws
        a = math.radians(90 + 120 * k)
        p = c + Vector((0.075 * math.cos(a), 0.075 * math.sin(a), 0.045))
        mb.cyl(p, p + Vector((0, 0, 0.02)), 0.006, 'stainless', seg=8)
    mb.cyl(c + Vector((0.06, 0, 0.02)), c + Vector((0.10, 0, 0.02)), 0.010, 'black_plastic', seg=10)  # connector
    d0 = c - Vector((0, 0, 0.012))
    if kind == 'sw':                       # double glass domes over a black detector
        mb.cyl(d0, d0 - Vector((0, 0, 0.002)), 0.022, 'black_body', seg=24)
        mb.lathe([(0.032 * math.cos(t), -0.032 * math.sin(t)) for t in [i * math.pi / 2 / 10 for i in range(11)]],
                 'dome', M=Matrix.Translation(d0), seg=40)
        mb.lathe([(0.020 * math.cos(t), -0.020 * math.sin(t)) for t in [i * math.pi / 2 / 8 for i in range(9)]],
                 'dome', M=Matrix.Translation(d0), seg=32)
    else:                                  # flat-ish silicon window (pyrgeometer)
        mb.cyl(d0, d0 - Vector((0, 0, 0.010)), 0.030, 'black_anod', r1=0.026, seg=32)
        mb.lathe([(0.026, 0.0), (0.024, -0.004), (0.016, -0.008), (0.0, -0.009)], 'lens_dark',
                 M=Matrix.Translation(d0 - Vector((0, 0, 0.010))), seg=32)


def build_sensors(mb):
    radiometer(mb, TIP + Vector((-0.28, 0, PLATE_C)), 'sw')
    radiometer(mb, TIP + Vector((0.28, 0, PLATE_C)), 'lw')
    # nadir IRT (Heitronics KT15-class head) hanging from the crossarm clamp
    mb.box(TIP + Vector((0, 0, -0.0525)), (0.06, 0.06, 0.065), 'aluminum')
    mb.cyl(TIP + Vector((0, 0, -0.08)), TIP + Vector((0, 0, -0.28)), 0.033, 'stainless', seg=28)
    mb.cyl(TIP + Vector((0, 0, -0.28)), TIP + Vector((0, 0, -0.34)), 0.036, 'black_anod', seg=28)
    mb.cyl(TIP + Vector((0, 0, -0.340)), TIP + Vector((0, 0, -0.343)), 0.018, 'lens_dark', seg=24)


L.part('gndrad_mast', coll, root, build_mast)
L.part('gndrad_sensors', coll, root, build_sensors)
L.empty('gndrad_psp', coll, root, tuple(TIP + Vector((-0.28, 0, PLATE_C))), 0.1)
L.empty('gndrad_pir', coll, root, tuple(TIP + Vector((0.28, 0, PLATE_C))), 0.1)
L.empty('gndirt', coll, root, tuple(TIP + Vector((0, 0, -0.34))), 0.1)

# guys: three directions avoiding the boom (boom -Y = 270 deg)
for k, az in enumerate((90, 210, 330)):
    a = math.radians(az)
    anchor = Vector((5.0 * math.cos(a), 5.0 * math.sin(a), 0.0))
    L.part(f'gndrad_anchor_{k}', coll, root, lambda mb, p=anchor: (
        mb.cyl(p + Vector((0, 0, 0.0)), p + Vector((0, 0, 0.12)), 0.02, 'galvanized', seg=10),
        mb.box(p + Vector((0, 0, 0.0)), (0.2, 0.2, 0.02), 'concrete')))
    for zg in (4.5, 9.0):
        top = Vector((0.065 * math.cos(a), 0.065 * math.sin(a), zg))
        L.wire(f'gndrad_guy_{k}_{int(zg)}', top, anchor + Vector((0, 0, 0.12)), 0.003, coll, root)

L.cable('gndrad_cable_up', [(0.04, -0.17, 1.70), (0.045, -0.05, 1.9), (0.045, -0.045, 5.0),
                            (0.045, -0.045, HB - 0.5), (0.10, -0.10, HB - 0.45)], 0.008, coll, root)
for x, nm in ((-0.28, 'psp'), (0.0, 'irt'), (0.28, 'pir')):
    L.cable(f'gndrad_cable_{nm}', [(0.10, -0.10, HB - 0.25), (0.06, -0.4, HB - 0.06), (x * 0.5, -1.4, HB - 0.03),
                                   (x, -BOOM + 0.12, HB - 0.04), (x + (0.1 if x >= 0 else 0.1), -BOOM, HB - 0.08)],
            0.004, coll, root)
L.cable('gndrad_cable_power', [(-0.08, -0.17, 1.20), (-0.08, -0.22, 0.6), (-0.10, -0.30, 0.06),
                               (-0.4, -0.7, 0.0), (-0.8, -1.1, 0.0)], 0.009, coll, root)

L.finish(NAME, coll, root,
         'Ground Radiometers on Stand for Upwelling Radiation (GNDRAD) with ground-viewing IRT',
         ['M1', 'S1'],
         ['ARM GNDRAD handbook ARM TR-027 (T. Stoffel, 2004): inverted unventilated PSP and PIR at 10 m AGL',
          'DERECHOS white paper Table 1 (SIRS upwelling components; GNDIRT / IRT row)'],
         f'Guyed 10 m tilt-down aluminium mast on a concrete pad; {BOOM:.0f} m boom to -Y at {HB:.0f} m; '
         'crossarm at the tip with inverted PSP-type pyranometer (empty gndrad_psp, -X), nadir IRT '
         '(gndirt, centre) and inverted PIR-type pyrgeometer (gndrad_pir, +X). Guys at 4.5 and 9 m '
         'to anchors 5 m out at az 90/210/330 deg (clear of the boom). Logger enclosure at 1.2-1.7 m. '
         'Sensor bodies and stand layout are generic.')
print('ALL DONE')
