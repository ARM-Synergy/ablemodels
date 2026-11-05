"""Rebuild S1 (Muscatine Island Research Farm) from mirf_s1.blend with linked assets."""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ablib as A
D = bpy.data
os.makedirs(os.path.join(A.REPO, 'scenes/S1/layers'), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(A.REPO, 'scenes/S1/S1.blend'), relative_remap=True)
A.fonts_to_mesh()
A.localize_images()

# --- plants: reuse M1 crops if identical, otherwise keep S1's own versions
bad = A.relink('plants/crops.blend', {'CornVariants': 'CornVariants', 'SoyVariants': 'SoyVariants'})
if bad:
    A.rename_collections({n: n + '_S1' for n in bad})
    A.extract('plants/crops_s1.blend', [n + '_S1' for n in bad])
# high-detail tree set used at S1/S2 (different meshes from the M1 set)
A.rename_collections({'TV_Spruce': 'TV_Spruce_HD', 'TV_Decid': 'TV_Decid_HD', 'TV_Far': 'TV_Far_HD',
                      'TreeParts': 'TreeParts_HD', 'TV_DecidBaked': 'TV_DecidBaked_HD'})
A.extract('plants/trees_hd.blend', ['TV_Spruce_HD', 'TV_Decid_HD', 'TV_Far_HD', 'TreeParts_HD', 'TV_DecidBaked_HD'])
A.extract('plants/native_flowers.blend', ['NativeFlowerVariants'])

A.extract('scenes/S1/layers/s1_terrain.blend', ['Terrain'])

# --- instruments: ECOR/SEBS prototypes (instanced by S1_Site empties)
for cn, rn, lib, libcns in [('INST_ECOR', 'ECOR_root', 'instruments/ECOR/ECOR.blend', ['INST_ECOR_4m', 'INST_ECOR']),
                            ('INST_SEBS', 'SEBS_root', 'instruments/SEBS/SEBS.blend', ['INST_SEBS'])]:
    done = False
    for libcn in libcns:
        bad = A.relink(lib, {cn: libcn}, roots={cn: rn})
        if not bad:
            done = True; break
    if not done:
        new = cn + '_S1'
        A.rename_collections({cn: new})
        A.extract_normalized(lib.replace('.blend', '_S1.blend'), [(new, rn)])

# --- structures
A.extract_normalized('buildings/center_pivots.blend',
                     [('Pivot_P1', 'Pivot_P1_root'), ('Pivot_P2', 'Pivot_P2_root'), ('Pivot_P3', 'Pivot_P3_root')])
A.extract('buildings/louisa_station.blend', ['LOUISA_Station', 'LOUISA_TreePoints'])
A.rename_collections({'Buildings': 'S1_MIRF_Buildings'})
A.extract('buildings/s1_mirf_buildings.blend', ['S1_MIRF_Buildings'])
A.extract('buildings/signs/sign_S1.blend', ['SIGN_S1'])

A.extract('scenes/S1/layers/s1_vegetation.blend', ['Vegetation'])
A.finish('scenes/S1/S1.blend', 'tools/reports/build_s1.json')
