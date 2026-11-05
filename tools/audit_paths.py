"""Check (and with --fix, repair) external paths in one .blend so the repo is self-contained.
blender -b file.blend --python tools/audit_paths.py -- report.json [--fix]
"""
import bpy, os, sys, json
args = sys.argv[sys.argv.index('--') + 1:]
fix = '--fix' in args
REPO = os.environ['ABLE_REPO']
here = bpy.data.filepath
rep = {'file': os.path.relpath(here, REPO), 'problems': [], 'fixed': []}


def inside_repo(p):
    return os.path.abspath(p).startswith(REPO + os.sep)


def check(kind, idname, raw, lib=None, packed=False):
    if not raw or raw == '<builtin>':
        return
    ab = bpy.path.abspath(raw, library=lib)
    bad = []
    if not raw.startswith('//'):
        bad.append('absolute')
    if not inside_repo(ab):
        bad.append('outside-repo')
    if not packed and not os.path.exists(ab):
        bad.append('missing')
    if bad:
        rep['problems'].append((kind, idname, raw, bad, packed))
    return bad


changed = False
for l in bpy.data.libraries:
    check('library', l.name, l.filepath)
for im in bpy.data.images:
    if im.library or im.source in ('VIEWER', 'GENERATED') or not im.filepath:
        continue
    bad = check('image', im.name, im.filepath, packed=bool(im.packed_file))
    if bad and im.packed_file and fix:
        import glob
        base = os.path.basename(im.filepath)
        hits = glob.glob(os.path.join(REPO, 'textures', '**', base), recursive=True)
        im.filepath_raw = bpy.path.relpath(hits[0]) if hits else '//' + base
        rep['fixed'].append(('packed image path', im.name, im.filepath_raw)); changed = True
for v in bpy.data.volumes:
    if not v.library:
        check('volume', v.name, v.filepath, packed=bool(v.packed_file))
for f in bpy.data.fonts:
    if not f.library:
        check('font', f.name, f.filepath, packed=bool(f.packed_file))
for s in bpy.data.scenes:
    if s.library:
        continue
    fp = s.render.filepath
    if fp and not fp.startswith('//') and fp not in ('/tmp/', '/tmp'):
        rep['problems'].append(('render.filepath', s.name, fp, ['absolute'], False))
        if fix:
            s.render.filepath = '//renders/'; rep['fixed'].append(('render.filepath', s.name)); changed = True
for o in bpy.data.objects:
    if o.library:
        continue
    for m in o.modifiers:
        bd = getattr(m, 'bake_directory', '')
        if bd:
            rep['problems'].append(('bake_directory', o.name, bd, ['bake'], False))
        if m.type == 'MESH_SEQUENCE_CACHE' and m.cache_file:
            check('cachefile', m.cache_file.name, m.cache_file.filepath)
if fix and changed:
    bpy.ops.wm.save_mainfile(compress=True)
json.dump(rep, open(args[0], 'w'), indent=1)
