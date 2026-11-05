"""Build a cloud asset file: mature snapshots of one simulation, each as its own collection.
blender -b <source_scene.blend> --python tools/build_clouds.py -- <spec.json>
spec: {"set": "cm1_supercell", "template": ["CM1_Storm"] | "prefix:LASSO_1740_",
       "normalize": true, "snapshots": [["name", "relative/src.vdb"], ...]}
VDBs larger than 50 MB are rewritten with 16-bit (half-float) storage; nothing is resampled.
"""
import bpy, os, sys, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ablib as A
spec = json.load(open(sys.argv[sys.argv.index('--') + 1]))
D = bpy.data
outdir = os.path.join(A.REPO, 'clouds', spec['set'])
os.makedirs(outdir, exist_ok=True)

t = spec['template']
if isinstance(t, str) and t.startswith('prefix:'):
    tmpl = sorted([o for o in D.objects if o.type == 'VOLUME' and o.name.startswith(t[7:])], key=lambda o: o.name)
else:
    tmpl = [D.objects[n] for n in t]
A.log('template objects', [o.name for o in tmpl])


def place_vdb(src_rel):
    src = os.path.join(A.SRC, src_rel)
    dst = os.path.join(outdir, os.path.basename(src))
    if os.path.exists(dst):
        return dst
    if os.path.getsize(src) > 50e6:
        import openvdb as vdb
        grids, meta = vdb.readAll(src)
        for g in grids:
            g.saveFloatAsHalf = True
        meta['ablemodels_note'] = 'rewritten with half-float storage from ' + os.path.basename(src)
        vdb.write(dst, grids, meta)
        A.log('half-float', os.path.basename(src), round(os.path.getsize(src) / 1e6), '->', round(os.path.getsize(dst) / 1e6), 'MB')
    else:
        shutil.copy2(src, dst)
    return dst


colls = []
for name, rel in spec['snapshots']:
    path = place_vdb(rel)
    vol = tmpl[0].data.copy()
    vol.name = name
    vol.filepath = path
    vol.is_sequence = False
    c = D.collections.new('CLOUD_' + name)
    bpy.context.scene.collection.children.link(c)
    for o in tmpl:
        n = o.copy(); n.data = vol; n.animation_data_clear()
        n.name = f'{name}_{o.name}' if len(tmpl) > 1 else name
        n.parent = None
        n.matrix_world = o.matrix_world.copy()
        if spec.get('normalize') and len(tmpl) == 1:
            n['source_location'] = list(o.matrix_world.translation)
            n.location = (0, 0, 0)
        c.objects.link(n)
    c['source_vdb'] = rel
    c['source_scene'] = os.path.basename(D.filepath)
    colls.append(c)
A.write_lib(f'clouds/{spec["set"]}/{spec["set"]}.blend', colls)
json.dump(A.REPORT, open(os.path.join(A.REPO, 'tools/reports', f'clouds_{spec["set"]}.json'), 'w'), indent=1, default=str)
