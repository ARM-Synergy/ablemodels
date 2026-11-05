"""Studio preview renders of library assets.
blender -b --factory-startup --python tools/render_previews.py -- jobs.json
Each job: {"lib": "instruments/AERI/AERI.blend", "coll": "INST_AERI", "out": "instruments/preview/AERI.jpg",
           "view": "34" | "aerial" | "lineup" | "cloud", "samples": 64, "res": [1280, 960]}
The world (sky) and sun are linked from scenes/M1/M1.blend so previews match the scenes.
"""
import bpy, sys, os, json, math
from mathutils import Vector, Matrix
REPO = os.environ.get('ABLE_REPO') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
jobs = json.load(open(sys.argv[sys.argv.index('--') + 1]))

# ---- one-time studio setup
sc = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
m1 = os.path.join(REPO, 'scenes/M1/M1.blend')
with bpy.data.libraries.load(m1, link=True, relative=False) as (s, d):
    d.worlds = ['World']
    d.objects = ['Sun']
sc.world = d.worlds[0]
sun = d.objects[0]
with bpy.data.libraries.load(m1, link=True, relative=False) as (s2, d2):
    d2.scenes = [s2.scenes[0]]
src = d2.scenes[0]
for attr in ('view_transform', 'look', 'exposure', 'gamma'):
    try:
        setattr(sc.view_settings, attr, getattr(src.view_settings, attr))
    except Exception as e:
        print('view setting', attr, e)
sc.display_settings.display_device = src.display_settings.display_device
sc.collection.objects.link(sun)
ground_mat = bpy.data.materials.new('PreviewGround')
ground_mat.use_nodes = True
bsdf = ground_mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (0.32, 0.30, 0.27, 1)
bsdf.inputs['Roughness'].default_value = 0.9
r = sc.render
r.engine = 'CYCLES'
sc.cycles.use_denoising = True
r.image_settings.file_format = 'JPEG'; r.image_settings.quality = 90
try:
    p = bpy.context.preferences.addons['cycles'].preferences
    p.compute_device_type = 'METAL'; p.get_devices()
    for dv in p.devices: dv.use = True
    sc.cycles.device = 'GPU'
except Exception as e:
    print('GPU setup failed', e)

cam_data = bpy.data.cameras.new('PreviewCam'); cam_data.lens = 50
cam = bpy.data.objects.new('PreviewCam', cam_data); sc.collection.objects.link(cam); sc.camera = cam


def link_coll(lib, name):
    with bpy.data.libraries.load(os.path.join(REPO, lib), link=True, relative=False) as (s, d):
        d.collections = [name]
    return d.collections[0]


def bounds(empties, trim=0.0):
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e18,) * 3); hi = Vector((-1e18,) * 3); n = 0
    pts = []
    for inst in dg.object_instances:
        if not inst.is_instance or inst.parent is None or inst.parent.original not in empties:
            continue
        o = inst.object
        if o.type in ('CAMERA', 'LIGHT', 'EMPTY'):
            continue
        for c in o.bound_box:
            w = inst.matrix_world @ Vector(c)
            pts.append(w)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w)); n += 1
    if trim and pts:
        import numpy as np
        a = np.array([tuple(p) for p in pts])
        lo = Vector(np.percentile(a, trim, axis=0)); hi = Vector(np.percentile(a, 100 - trim, axis=0))
    return lo, hi, n


def frame(lo, hi, view, res, j_tight=0.72, zfrac=0.5):
    ctr = (lo + hi) / 2; ext = hi - lo
    ctr.z = lo.z + zfrac * ext.z
    rad = max(ext.length / 2, 0.3)
    d = {'34': Vector((-1.0, -1.35, 0.62)), 'aerial': Vector((-0.75, -1.0, 1.15)),
         'lineup': Vector((0.0, -1.0, 0.28)), 'cloud': Vector((-0.6, -1.0, 0.22)),
         'top': Vector((0.0, -0.02, 1.0)), 'front_x': Vector((1.0, -0.35, 0.22))}[view].normalized()
    half = math.atan(18.0 / cam_data.lens) * (min(res) / max(res) if res[0] >= res[1] else 1)
    dist = rad / math.sin(half) * j_tight
    cam.location = ctr + d * dist
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam_data.clip_start = max(0.01, dist / 2000); cam_data.clip_end = dist * 4 + ext.length * 2
    return ctr, ext


made = []
for j in jobs:
    if j.get('scene_view'):   # site layers spread over kilometres read better in their scene
        import shutil
        shutil.copy(os.path.join(REPO, j['scene_view']), os.path.join(REPO, j['out']))
        continue
    res = j.get('res', [1280, 960]); r.resolution_x, r.resolution_y = res; r.resolution_percentage = 100
    sc.cycles.samples = j.get('samples', 64)
    # cloud scenes in the working files use deep volume scattering
    sc.cycles.volume_bounces = j.get('volume_bounces', 16) if j.get('view') == 'cloud' else 1
    sc.cycles.max_bounces = 20 if j.get('view') == 'cloud' else 4
    sc.cycles.sample_clamp_indirect = 10.0
    view = j.get('view', '34')
    coll = link_coll(j['lib'], j['coll'])
    for ob in coll.all_objects:          # volume bounds are only known once the grids are read
        if ob.type == 'VOLUME':
            ob.data.grids.load()
    empties = []
    if view == 'lineup':
        objs = sorted([o for o in coll.all_objects if o.type in ('MESH', 'CURVE', 'VOLUME') and o.parent is None], key=lambda o: o.name)
        x = 0.0
        for o in objs:
            dims = Vector(o.dimensions) if any(o.dimensions) else Vector((1, 1, 1))
            if dims.length == 0: dims = Vector((1, 1, 1))
            c = bpy.data.collections.new('LU_' + o.name); c.objects.link(o)
            c.instance_offset = o.matrix_world.translation
            e = bpy.data.objects.new('LU_' + o.name, None); e.instance_type = 'COLLECTION'; e.instance_collection = c
            w = max(dims.x, dims.y, 0.2)
            e.location = (x + w / 2, 0, 0); x += w * 1.25
            sc.collection.objects.link(e); empties.append(e)
    else:
        e = bpy.data.objects.new('PV_' + j['coll'], None); e.instance_type = 'COLLECTION'; e.instance_collection = coll
        sc.collection.objects.link(e); empties.append(e)
    bpy.context.view_layer.update()
    lo, hi, n = bounds(empties, j.get('trim', 0.0))
    if n == 0:
        print('NOTHING TO FRAME', j); continue
    if view == 'cloud':
        ctr = (lo + hi) / 2; ext = hi - lo
        L = sun.matrix_world.to_3x3() @ Vector((0, 0, -1))
        h = Vector((L.x, L.y, 0)).normalized()
        wide = max(ext.x, ext.y)
        if wide > 20000:   # periodic LES field: stand inside it
            cam_data.lens = 20
            cam.location = Vector((ctr.x, ctr.y, 2.0)) - h * (0.18 * wide)
            target = cam.location + h * 10000 + Vector((0, 0, 2600))
        else:              # single storm: elevated, sun behind, whole cell in view
            cam_data.lens = 35
            cam.location = Vector((ctr.x, ctr.y, j.get('cam_z', 3000.0))) - h * (j.get('dist', 2.2) * wide)
            target = Vector((ctr.x, ctr.y, lo.z + 0.3 * ext.z))
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam_data.clip_start = 0.5; cam_data.clip_end = wide * 6
        ctr = Vector((cam.location.x, cam.location.y, 0)); ext = Vector((wide, wide, ext.z))
    else:
        cam_data.lens = 50
        ctr, ext = frame(lo, hi, view, res, j.get('tight', 0.72 if view in ('34', 'lineup') else 0.85), j.get('zfrac', 0.5))
    gsize = max(ext.x, ext.y, 1.0) * (40 if view != 'cloud' else 12)
    bpy.ops.mesh.primitive_plane_add(size=gsize, location=(ctr.x, ctr.y, lo.z - 0.002 if view != 'cloud' else 0.0))
    g = bpy.context.active_object; g.data.materials.append(ground_mat)
    out = os.path.join(REPO, j['out']); os.makedirs(os.path.dirname(out), exist_ok=True)
    r.filepath = out
    bpy.ops.render.render(write_still=True)
    made.append(j['out']); print('PREVIEW', j['out'], flush=True)
    # clean up for the next job
    bpy.data.objects.remove(g)
    for e in empties:
        ic = e.instance_collection
        bpy.data.objects.remove(e)
        if ic.name.startswith('LU_'):
            bpy.data.collections.remove(ic)
print('PREVIEWS_DONE', len(made))
