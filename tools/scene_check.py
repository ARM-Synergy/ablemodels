"""Evaluate a scene and write a fingerprint (instance counts, vertex totals, transform sums)
plus optional low-res test renders, so a rebuilt scene can be compared with its source.
blender -b scene.blend --python tools/scene_check.py -- out_prefix [cam1,cam2] [hide_colls]
"""
import bpy, sys, json, os
args = sys.argv[sys.argv.index('--') + 1:]
out = args[0]
cams = args[1].split(',') if len(args) > 1 and args[1] else []
sc = bpy.context.scene
if len(args) > 2 and args[2] == 'fiximg':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ablib
    for img in bpy.data.images:
        if img.library or img.packed_file or not img.filepath or img.source in ('VIEWER', 'GENERATED'):
            continue
        p = ablib.resolve_src(img.filepath)
        if p: img.filepath = p
dg = bpy.context.evaluated_depsgraph_get()
from collections import defaultdict
n = defaultdict(int); verts = defaultdict(int); tsum = [0.0, 0.0, 0.0]
for inst in dg.object_instances:
    o = inst.object
    if not inst.show_self: continue
    n[o.type] += 1
    if o.type == 'MESH':
        verts['mesh'] += len(o.data.vertices)
    if o.type == 'EMPTY': continue
    t = inst.matrix_world.translation
    tsum[0] += t.x; tsum[1] += t.y; tsum[2] += t.z
fp = {'instances': dict(n), 'verts': dict(verts), 'tsum': [round(v, 1) for v in tsum],
      'libs': [l.filepath for l in bpy.data.libraries],
      'missing_libs': [l.filepath for l in bpy.data.libraries if not os.path.exists(bpy.path.abspath(l.filepath))]}
json.dump(fp, open(out + '_fp.json', 'w'), indent=1)
r = sc.render
r.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.seed = 0; sc.cycles.use_denoising = False
r.resolution_x, r.resolution_y, r.resolution_percentage = 640, 360, 100
r.image_settings.file_format = 'PNG'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'; prefs.get_devices()
    for d in prefs.devices: d.use = True
    sc.cycles.device = 'GPU'
except Exception as e:
    print('gpu setup failed', e)
for c in cams:
    if c not in bpy.data.objects: print('no camera', c); continue
    sc.camera = bpy.data.objects[c]
    r.filepath = f'{out}_{c}.png'
    bpy.ops.render.render(write_still=True)
print('CHECK_DONE')
