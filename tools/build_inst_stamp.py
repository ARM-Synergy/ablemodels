"""ARM STAMP soil temperature and moisture profile station -> instruments/STAMP/STAMP.blend
(collection INST_STAMP).   blender -b --factory-startup --python tools/build_inst_stamp.py

From the STAMP handbook (DOE/SC-ARM-TR-186, D. R. Cook): three profiles (west, south,
east) about 1 m apart, each with Stevens HydraProbes at 5, 10, 20, 50 and 100 cm pushed
into the side of a hand-augered hole (15 probes); electronics (Campbell CR800 +
multiplexer + battery) in an enclosure on a pole in a concrete foundation placed away from
the probes; Texas Electronics TR-525M heated tipping-bucket gauge (245 mm knife-edge
collector, 305 mm tall).

Everything below z = 0 (probes, cables in the holes, conduit) is modelled so cut-away or
x-ray views work; at the surface you see the backfilled auger holes, marker stakes, the
conduit trench, the enclosure pole and the rain gauge. Hole spacing and the 3 m offset to
the enclosure are generic.
"""
import bpy, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instlib as L

NAME = 'STAMP'
coll, root = L.start(NAME)
DEPTHS = [0.05, 0.10, 0.20, 0.50, 1.00]
# profiles 1 m apart, 3 m south of the enclosure pole; probes point away from the centre
PC = Vector((0, -3.0, 0))
PROFILES = {'west': (PC + Vector((-1.0, 0.0, 0)), Vector((-1, 0, 0))),
            'south': (PC + Vector((0.0, -1.0, 0)), Vector((0, -1, 0))),
            'east': (PC + Vector((1.0, 0.0, 0)), Vector((1, 0, 0)))}
GAUGE = Vector((1.0, 0.3, 0))


def build_holes(mb):
    for name, (p, d) in PROFILES.items():
        mb.cyl(p + Vector((0, 0, 0.0)), p + Vector((0, 0, 0.012)), 0.16, 'soil_fresh', r1=0.10, seg=24)  # mound
        # marker stake with flag tape on the side away from the probes
        s = p - d * 0.25
        mb.box(s + Vector((0, 0, 0.31)), (0.02, 0.02, 0.62), 'grey_paint')
        mb.box(s + Vector((0, 0, 0.60)), (0.03, 0.03, 0.05), 'orange_flag')


def build_backfill(mb):
    for name, (p, d) in PROFILES.items():
        mb.cyl(p + Vector((0, 0, -1.05)), p + Vector((0, 0, 0.0)), 0.05, 'soil_fresh', seg=20)
        s = p - d * 0.25
        mb.box(s + Vector((0, 0, -0.15)), (0.02, 0.02, 0.30), 'grey_paint')          # driven part of the stake


def hydraprobe(mb, p, d):
    """Stevens HydraProbe: 42 mm x 124 mm body, 4 tines 57 mm, body axis along d."""
    body0 = p + d * 0.06
    body1 = body0 + d * 0.124
    mb.cyl(p, body0, 0.004, 'cable', seg=8)
    mb.cyl(body0, body1, 0.021, 'white_plastic', seg=20)
    mb.cyl(body1, body1 + d * 0.006, 0.021, 'stainless', seg=20)
    side = Vector((-d.y, d.x, 0))
    tips = [Vector((0, 0, 0))] + [side * 0.011 * math.cos(a) + Vector((0, 0, 0.011 * math.sin(a)))
                                  for a in (math.radians(90), math.radians(210), math.radians(330))]
    for t in tips:
        mb.cyl(body1 + t, body1 + t + d * 0.057, 0.0015, 'stainless', seg=6)


def build_probes(mb):
    for name, (p, d) in PROFILES.items():
        for z in DEPTHS:
            hydraprobe(mb, p + d * 0.04 + Vector((0, 0, -z)), d)


def build_station(mb):
    """Everything at or above the surface."""
    mb.cyl((0, 0, 0.0), (0, 0, 0.04), 0.15, 'concrete', seg=24)                       # footing top
    mb.cyl((0, 0, 0.0), (0, 0, 1.80), 0.0302, 'galvanized', seg=20)
    mb.cyl((0, 0, 1.80), (0, 0, 1.82), 0.033, 'black_plastic', seg=20)
    for z in (0.95, 1.55):
        mb.box((0, -0.045, z), (0.40, 0.04, 0.04), 'galvanized')
        mb.box((0, -0.03, z), (0.08, 0.03, 0.07), 'stainless')
    mb.box((0, -0.18, 1.25), (0.42, 0.22, 0.56), 'fiberglass_white')
    mb.box((0, -0.294, 1.25), (0.40, 0.008, 0.54), 'fiberglass_white')
    mb.box((0, -0.299, 1.42), (0.12, 0.002, 0.05), 'label')
    for x in (-0.18, 0.18):
        for z in (1.03, 1.47):
            mb.cyl((x, -0.298, z), (x, -0.308, z), 0.012, 'stainless', seg=10)
    # PVC conduits rising into the enclosure bottom (signal, power)
    mb.cyl((0.05, -0.18, 0.0), (0.05, -0.18, 0.97), 0.021, 'pvc_grey', seg=16)
    mb.cyl((-0.08, -0.18, 0.0), (-0.08, -0.18, 0.97), 0.013, 'pvc_grey', seg=12)
    mb.cyl((0.25, 0.15, 0.0), (0.25, 0.15, 0.08), 0.008, 'copper', seg=8)              # ground rod top
    # surface scar over the conduit trench to the profile centre
    mb.beam(Vector((0.05, -0.45, 0.002)), PC + Vector((0, 0.05, 0.002)), 0.22, 0.008, 'soil_fresh')
    # TR-525M heated rain gauge on its own pole, rim at 1.0 m
    g = GAUGE
    mb.cyl(g, g + Vector((0, 0, 0.04)), 0.12, 'concrete', seg=20)
    mb.cyl(g, g + Vector((0, 0, 0.66)), 0.0302, 'galvanized', seg=20)
    mb.box(g + Vector((0, 0, 0.68)), (0.22, 0.22, 0.012), 'galvanized')
    rim = 0.1225
    mb.lathe([(0.11, 0.69), (0.123, 0.70), (0.128, 0.72), (0.128, 0.985), (rim + 0.002, 0.995),
              (rim, 1.0), (rim - 0.002, 0.995), (0.118, 0.985), (0.03, 0.83), (0.012, 0.82)],
             'aluminum', M=Matrix.Translation(g), seg=48)
    mb.box(g + Vector((0, -0.135, 0.76)), (0.06, 0.02, 0.04), 'black_plastic')        # heater/connector


def build_station_buried(mb):
    """Footings, buried pole ends, conduit at 0.3 m and the ground rod."""
    mb.cyl((0, 0, -0.60), (0, 0, 0.0), 0.15, 'concrete', seg=24)
    mb.cyl((0, 0, -0.55), (0, 0, 0.0), 0.0302, 'galvanized', seg=20)
    mb.cyl((0.05, -0.18, -0.30), (0.05, -0.18, 0.0), 0.021, 'pvc_grey', seg=16)
    mb.cyl((0.05, -0.18, -0.30), (0.05, -0.60, -0.30), 0.021, 'pvc_grey', seg=16)
    mb.cyl((-0.08, -0.18, -0.30), (-0.08, -0.18, 0.0), 0.013, 'pvc_grey', seg=12)
    mb.cyl((0.25, 0.15, -0.8), (0.25, 0.15, 0.0), 0.008, 'copper', seg=8)
    mb.cyl(Vector((0.05, -0.60, -0.30)), PC + Vector((0, 0.15, -0.30)), 0.021, 'pvc_grey', seg=16)
    g = GAUGE
    mb.cyl(g + Vector((0, 0, -0.50)), g, 0.12, 'concrete', seg=20)
    mb.cyl(g + Vector((0, 0, -0.45)), g, 0.0302, 'galvanized', seg=20)


BG = L.below(coll)
L.part('stamp_surface', coll, root, build_holes)
L.part('stamp_station', coll, root, build_station)
L.part('stamp_backfill', BG, root, build_backfill)
L.part('stamp_hydraprobes', BG, root, build_probes)
L.part('stamp_station_buried', BG, root, build_station_buried)
for name, (p, d) in PROFILES.items():
    L.empty(f'stamp_profile_{name}', coll, root, tuple(p), 0.15)
    # bundle of probe leads up the hole and into the trench
    L.cable(f'stamp_leads_{name}', [tuple(p + Vector((0, 0, -1.0))), tuple(p + Vector((0, 0, -0.5))),
                                    tuple(p + Vector((0, 0, -0.32))), tuple(p.lerp(PC, 0.6) + Vector((0, 0.05, -0.30))),
                                    tuple(PC + Vector((0, 0.15, -0.30)))], 0.008, BG, root)
L.cable('stamp_gauge_cable', [tuple(GAUGE + Vector((0, -0.135, 0.74))), tuple(GAUGE + Vector((0, -0.04, 0.55))),
                              tuple(GAUGE + Vector((0, -0.035, 0.05))), (0.6, -0.1, 0.0),
                              (0.2, -0.2, 0.0), (0.05, -0.2, 0.30)], 0.005, coll, root)

L.finish(NAME, coll, root,
         'Soil Temperature and Moisture Profiles (STAMP) station',
         ['M1', 'S1'],
         ['ARM STAMP handbook DOE/SC-ARM-TR-186 (D. R. Cook, 2018): 3 profiles ~1 m apart, HydraProbes at 5/10/20/50/100 cm, '
          'CR800 enclosure on a pole in concrete, TR-525M heated gauge (245 mm collector, 305 mm tall)',
          'Stevens HydraProbe dimensions 42 x 124 mm, 57 mm tines',
          'DERECHOS white paper section 3.1 / errata: soil-moisture profiles requested at M1 and S1'],
         'Enclosure pole at the origin (door -Y), TR-525M gauge 1 m east/0.3 m north (rim 1.0 m AGL). '
         'Profiles west/south/east 1 m from a centre 3 m south of the pole (empties stamp_profile_*), each '
         'with five HydraProbes below ground pointing away from the centre; leads run in a buried PVC '
         'conduit at 0.3 m. Underground parts are real geometry in STAMP_BelowGrade (hidden; un-hide for cut-aways).')
print('ALL DONE')
