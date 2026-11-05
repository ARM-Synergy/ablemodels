"""Build the test scenes in scenes/tests/.
blender -b <base.blend or nothing> --python tools/build_tests.py -- <test-name>
"""
import bpy, os, sys, glob
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ablib as A
name = sys.argv[sys.argv.index('--') + 1]
D = bpy.data
out = os.path.join(A.REPO, 'scenes/tests', name + '.blend')
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=out, relative_remap=True)   # paths now relative to tests/


def link(lib, colls=(), objs=(), worlds=()):
    with D.libraries.load(os.path.join(A.REPO, lib), link=True, relative=True) as (s, d):
        d.collections = list(colls); d.objects = list(objs); d.worlds = list(worlds)
    return d


def instance(coll, matrix=Matrix.Identity(4), parent=None, name=None):
    e = D.objects.new(name or coll.name + '_inst', None)
    e.instance_type = 'COLLECTION'; e.instance_collection = coll; e.matrix_world = matrix
    (parent or bpy.context.scene.collection).objects.link(e)
    return e


def camera_from(src_blend, cam_name, new_name):
    """Copy a camera's evaluated transform and lens out of one of the original working files
    (evaluated in a separate Blender process so parents/constraints are applied)."""
    import subprocess, json, tempfile
    tmp = tempfile.mktemp(suffix='.json')
    code = ("import bpy,json;o=bpy.data.objects[%r];dg=bpy.context.evaluated_depsgraph_get();e=o.evaluated_get(dg);"
            "json.dump({'m':[list(r) for r in e.matrix_world],'lens':o.data.lens,'clip':o.data.clip_end,"
            "'sw':o.data.sensor_width},open(%r,'w'))") % (cam_name, tmp)
    subprocess.run([bpy.app.binary_path, '-b', src_blend, '--python-expr', code], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = json.load(open(tmp))
    cd = D.cameras.new(new_name); cd.lens = d['lens']; cd.clip_end = d['clip']; cd.sensor_width = d['sw']
    cam = D.objects.new(new_name, cd); cam.matrix_world = Matrix(d['m'])
    bpy.context.scene.collection.objects.link(cam)
    return cam


clouds = D.collections.get('Clouds') or D.collections.new('Clouds')
if name != 'instrument_lineup' and 'Clouds' not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(clouds)

if name == 'm1_supercell':
    c = link('clouds/cm1_supercell/cm1_supercell.blend', ['CLOUD_supercell_c100_t25']).collections[0]
    # same storm placement as farm_v5_storm_studio.blend
    instance(c, Matrix.Translation((-34948.7, -11251.7, 0.0)), clouds)
    cam = camera_from(os.path.join(A.SRC, 'farm_v5_storm_studio.blend'), 'Cam_Storm_Sign', 'Cam_Storm_Sign')
    bpy.context.scene.camera = cam

elif name == 'm1_lasso_cumulus':
    c = link('clouds/lasso_sgp_20170403/lasso_sgp_20170403.blend', ['CLOUD_lasso8_2040']).collections[0]
    instance(c, Matrix.Identity(4), clouds)
    bpy.context.scene.camera = D.objects['Cam_M1_Aerial_SE']

elif name == 's1_ucla_cumulus':
    c = link('clouds/ucla_cumulus/ucla_cumulus.blend', ['CLOUD_ucla_t6600']).collections[0]
    instance(c, Matrix.Identity(4), clouds)
    bpy.context.scene.camera = D.objects['Cam_Aerial_SW']

elif name == 'instrument_lineup':
    for o in list(D.objects):
        D.objects.remove(o)
    d = link('scenes/M1/M1.blend', objs=['Sun'], worlds=['World'])
    sc = bpy.context.scene
    sc.world = d.worlds[0]; sc.collection.objects.link(d.objects[0])
    row = D.collections.new('Instruments'); sc.collection.children.link(row)
    libs = sorted(glob.glob(os.path.join(A.REPO, 'instruments/*/*.blend')))
    x = 0.0
    for lib in libs:
        rel = os.path.relpath(lib, A.REPO)
        with D.libraries.load(lib, link=True, relative=True) as (s, dd):
            dd.collections = [n for n in s.collections if n.startswith('INST_')]
        for c in dd.collections:
            w = 14.0 if 'CSAPR2' in c.name else 4.0
            instance(c, Matrix.Translation((x + w / 2, 0, 0)), row)
            x += w
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x / 2, 0, 0))
    g = bpy.context.active_object; g.name = 'Ground'; g.scale = (x + 600, 600, 1)
    m = D.materials.new('Gravel'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.3, 0.29, 0.26, 1)
    g.data.materials.append(m)
    cd = D.cameras.new('Cam_Lineup'); cd.lens = 35
    cam = D.objects.new('Cam_Lineup', cd); sc.collection.objects.link(cam)
    cam.location = (x / 2, -x * 0.95, 10.0)
    cam.rotation_euler = (Vector((x / 2, 0, 2.5)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 64
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080

if name != 'instrument_lineup':
    # light-path settings of the original cloud scenes (multiple scattering in the clouds)
    cy = bpy.context.scene.cycles
    cy.volume_bounces = 64; cy.max_bounces = 68; cy.samples = 64
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_as_mainfile(filepath=out, compress=True, relative_remap=True)
print('TEST_SAVED', out, os.path.getsize(out))
