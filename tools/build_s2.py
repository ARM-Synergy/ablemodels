"""Rebuild S2 (Washington Municipal Airport, KAWG) from airport_awg.blend with linked assets."""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ablib as A
D = bpy.data
os.makedirs(os.path.join(A.REPO, 'scenes/S2/layers'), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(A.REPO, 'scenes/S2/S2.blend'), relative_remap=True)
A.fonts_to_mesh()
A.localize_images()

# --- plants
bad = A.relink('plants/crops.blend', {'CornVariants': 'CornVariants', 'SoyVariants': 'SoyVariants'})
if bad and os.path.exists(os.path.join(A.REPO, 'plants/crops_s1.blend')):
    bad = A.relink('plants/crops_s1.blend', {n: n + '_S1' for n in bad})
if bad:
    A.rename_collections({n: n + '_S2' for n in bad})
    A.extract('plants/crops_s2.blend', [n + '_S2' for n in bad])
bad = A.relink('plants/grasses.blend', {'GrassVariants': 'GrassVariants', 'TallGrassVariants': 'TallGrassVariants'})
if bad:
    A.rename_collections({n: n + '_S2' for n in bad})
    A.extract('plants/grasses_s2.blend', [n + '_S2' for n in bad])
bad = A.relink('plants/trees_hd.blend', {'TV_DecidBaked': 'TV_DecidBaked_HD'})
if bad:
    A.rename_collections({'TV_DecidBaked': 'TV_DecidBaked_S2'})
    A.extract('plants/trees_s2.blend', ['TV_DecidBaked_S2'])

A.extract('scenes/S2/layers/s2_terrain.blend', ['Terrain'])

# --- instruments, aircraft, SACR container
A.extract_normalized('instruments/CSAPR2/CSAPR2.blend', [('CSAPR2', 'CSAPR2_root')])
A.rename_collections({'AWOS_KAWG': 'INST_AWOS'})
A.extract_normalized('instruments/AWOS/AWOS.blend', [('INST_AWOS', 'AWOS_root')])
A.extract_normalized('vehicles/c850_arm.blend', [('C850_ARM', 'C850_root')])
site = D.collections['S1_Site']
pairs = A.collection_from_roots(site, ['AMF2_Cont_7_SACR'], lambda r: 'CONT_7_SACR')
if not A.relink_normalized('containers/amf2_containers.blend', 'CONT_7_SACR', 'AMF2_Cont_7_SACR'):
    A.rename_collections({'CONT_7_SACR': 'CONT_7_SACR_S2'})
    A.extract_normalized('containers/sacr_container_s2.blend', [('CONT_7_SACR_S2', 'AMF2_Cont_7_SACR')])

# --- buildings and site infrastructure
A.rename_collections({'Buildings': 'S2_KAWG_Buildings'})
A.extract('buildings/s2_kawg_buildings.blend', ['S2_KAWG_Buildings'])
A.extract('buildings/signs/sign_S2.blend', ['SIGN_S2'])
A.extract('scenes/S2/layers/s2_power_roads.blend', ['S1_Power_Roads'])
A.extract('scenes/S2/layers/s2_vegetation.blend', ['Vegetation'])
A.finish('scenes/S2/S2.blend', 'tools/reports/build_s2.json')
