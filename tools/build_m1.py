"""Rebuild the M1 (main site, farm) scene from farm_v5.blend with linked assets.
blender -b <src>/farm_v5.blend --python tools/build_m1.py
"""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ablib as A

D = bpy.data
os.makedirs(os.path.join(A.REPO, 'scenes/M1/layers'), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(A.REPO, 'scenes/M1/M1.blend'), relative_remap=True)
A.fonts_to_mesh()
A.localize_images()

# --- plants (prototype collections used by geometry-node scatterers)
A.extract('plants/crops.blend', ['CornVariants', 'SoyVariants'])
A.extract('plants/grasses.blend', ['GrassVariants', 'TallGrassVariants'])
A.extract('plants/trees.blend', ['TreeVariants', 'TV_Decid', 'TV_Spruce', 'TV_Far', 'TreeParts'])

# --- ground first: other layers conform to the Ground terrain object
A.extract('scenes/M1/layers/m1_ground.blend', ['Ground'])

# --- instruments: one file per instrument, root at origin
inst = [c.name for c in D.collections['Instruments_v4'].children if c.name.startswith('INST_')]
for cn in inst:
    name = cn[5:]
    root = next(o for o in D.collections[cn].objects if o.name.startswith(name + '_root'))
    specs = [(cn, root.name)]
    if name == 'ECOR' and 'INST_ECOR_4m' in D.collections:
        r4 = next(o for o in D.collections['INST_ECOR_4m'].objects if o.name.startswith('ECOR_root'))
        specs.append(('INST_ECOR_4m', r4.name))
    A.extract_normalized(f'instruments/{name}/{name}.blend', specs)

# --- containers: each AMF2 container/shelter becomes its own asset
amf = D.collections['AMF2']
A.split_out_local(amf)
roots = [o.name for o in amf.objects if o.type == 'EMPTY' and o.parent is None and
         (o.name.startswith('AMF2_Cont_') or o.name in ('AOS_Platform', 'AMF2_OfficeShelter', 'AMF2_RentalContainer'))]
def cname(r):
    return 'CONT_' + r.replace('AMF2_Cont_', '').replace('AMF2_', '')
cont = D.collections.new('Containers'); bpy.context.scene.collection.children.link(cont)
pairs = A.collection_from_roots(amf, roots, cname, cont)
A.extract_normalized('containers/amf2_containers.blend', [(c.name, r.name) for c, r in pairs])

# --- vehicles: each farm vehicle is an asset at the origin
veh = D.collections['Vehicles']
vroots = [o.name for o in veh.objects if o.parent is None]
pairs = A.collection_from_roots(veh, vroots, lambda r: 'VEH_' + r)
A.extract_normalized('vehicles/farm_vehicles.blend', [(c.name, r.name) for c, r in pairs])

# --- buildings / structures
A.extract('buildings/m1_farmstead.blend', ['Farmstead'])
fp = D.collections['Flagpole']
r = A.make_root(fp, 'Flagpole_root', D.objects['Flagpole_Base'])
A.extract_normalized('buildings/flagpole.blend', [('Flagpole', 'Flagpole_root')])
A.extract('buildings/signs/sign_M1.blend', ['SIGN_M1'])

# --- remaining site layers
A.extract('scenes/M1/layers/m1_fields.blend', ['Fields'])
A.extract('scenes/M1/layers/m1_amf2_site.blend', ['AMF2'])

A.finish('scenes/M1/M1.blend', 'tools/reports/build_m1.json')
