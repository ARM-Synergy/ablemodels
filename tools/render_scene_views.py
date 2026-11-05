"""Render preview stills of a scene from its own cameras (scene lighting and settings kept).
blender -b scenes/M1/M1.blend --python tools/render_scene_views.py -- <out_prefix> <cam1,cam2,...> [samples] [WxH]
"""
import bpy, sys, os
args = sys.argv[sys.argv.index('--') + 1:]
prefix, cams = args[0], args[1].split(',')
spp = int(args[2]) if len(args) > 2 else 96
sc = bpy.context.scene; r = sc.render
r.engine = 'CYCLES'; sc.cycles.samples = spp; sc.cycles.use_denoising = True
w, h = (int(v) for v in args[3].split('x')) if len(args) > 3 else (1600, 900)
r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
if len(args) > 4:   # preview-only cap on volume bounces (the scene file keeps its own setting)
    sc.cycles.volume_bounces = min(sc.cycles.volume_bounces, int(args[4]))
r.image_settings.file_format = 'JPEG'; r.image_settings.quality = 90
try:
    p = bpy.context.preferences.addons['cycles'].preferences
    p.compute_device_type = 'METAL'; p.get_devices()
    for d in p.devices: d.use = True
    sc.cycles.device = 'GPU'
except Exception as e:
    print('GPU setup failed', e)
for c in cams:
    sc.camera = bpy.data.objects[c]
    r.filepath = f'{prefix}_{c}.jpg'
    bpy.ops.render.render(write_still=True)
    print('VIEW', r.filepath, flush=True)
