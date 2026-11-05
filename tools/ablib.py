"""Helpers for building the ablemodels asset library from monolithic scene files.

Run inside Blender (background mode). Environment:
  ABLE_REPO  repository root
  ABLE_SRC   root of the original farm_amf2 working folder (source scenes/textures)

Two ways an embedded collection is moved into a library file:
  extract()            collection keeps world coordinates and is linked back in place
                       (site-specific layers: terrain, fields, buildings at a site)
  extract_normalized() collection's root object is moved to the origin, written,
                       and the scene gets a collection-instance empty at the old
                       transform (re-usable assets: instruments, containers, vehicles)
Both are lossless: geometry, materials and modifiers are written unchanged.
"""
import bpy, os, re, shutil, json
from mathutils import Matrix

REPO = os.environ.get('ABLE_REPO', '')
SRC = os.environ.get('ABLE_SRC', '')
REPORT = {'written': [], 'linked': [], 'missing': [], 'warnings': [], 'mismatch': []}


def log(*a):
    print('[able]', *a, flush=True)


def warn(*a):
    s = ' '.join(map(str, a)); REPORT['warnings'].append(s); log('WARN', s)


# ---------------------------------------------------------------- paths
def resolve_src(path):
    if not path:
        return None
    p = bpy.path.abspath(path)
    if os.path.exists(p):
        return os.path.normpath(p)
    m = re.search(r'farm_amf2/(.*)$', path.replace('\\', '/'), re.I)
    if m:
        cand = os.path.join(SRC, m.group(1))
        if os.path.exists(cand):
            return os.path.normpath(cand)
    return None


def texture_dest(src):
    s = src.replace('\\', '/')
    fn = os.path.basename(s)
    m = re.search(r'/_tex/([^/]+)/', s)
    if m:
        return os.path.join(REPO, 'textures', 'pbr', m.group(1), fn)
    if '/mirf_s1/' in s:
        return os.path.join(REPO, 'textures', 'imagery', 's1_mirf', fn)
    if '/airport_awg/' in s:
        return os.path.join(REPO, 'textures', 'imagery', 's2_kawg', fn)
    if 'flag_' in fn:
        return os.path.join(REPO, 'textures', 'flags', fn)
    if '/signs/' in s:
        return os.path.join(REPO, 'textures', 'signs', fn)
    if '/lasso/' in s or '/m1_lidar/' in s:
        return os.path.join(REPO, 'textures', 'imagery', 'm1', fn)
    return os.path.join(REPO, 'textures', 'misc', fn)


def localize_images():
    """Copy every referenced (unpacked) image into REPO/textures and point at it."""
    n = 0
    for img in bpy.data.images:
        if img.library or img.packed_file or img.source in ('VIEWER', 'GENERATED') or not img.filepath:
            continue
        src = resolve_src(img.filepath)
        if not src:
            REPORT['missing'].append(('image', img.name, img.filepath))
            warn('missing image', img.name, img.filepath)
            continue
        dst = texture_dest(src)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
        img.filepath = dst
        n += 1
    log('localized images', n)


def fonts_to_mesh():
    """Text objects using non-builtin (system) fonts become meshes so files are portable."""
    dg = bpy.context.evaluated_depsgraph_get()
    for o in list(bpy.data.objects):
        if o.library or o.type != 'FONT':
            continue
        f = o.data.font
        if f is None or f.filepath == '<builtin>' or f.packed_file:
            continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        name = o.name
        new = bpy.data.objects.new(name + '_mesh', me)
        new.parent = o.parent
        new.matrix_parent_inverse = o.matrix_parent_inverse.copy()
        new.matrix_basis = o.matrix_basis.copy()
        new.hide_render = o.hide_render; new.hide_viewport = o.hide_viewport
        for c in o.users_collection:
            c.objects.link(new)
        for ch in o.children:
            mw = ch.matrix_world.copy(); ch.parent = new; ch.matrix_world = mw
        bpy.data.objects.remove(o)
        new.name = name
        log('font->mesh', name, f.filepath)


# ---------------------------------------------------------------- view layer flags
def _walk_lc(lc, out):
    out[lc.collection] = (lc.exclude, lc.hide_viewport, lc.collection.hide_render, lc.collection.hide_viewport)
    for ch in lc.children:
        _walk_lc(ch, out)


def layer_flags(coll):
    out = {}
    for sc in bpy.data.scenes:
        for vl in sc.view_layers:
            d = {}
            _walk_lc(vl.layer_collection, d)
            if coll in d:
                out[(sc.name, vl.name)] = d[coll]
    return out


def apply_layer_flags(coll, flags):
    for (scn, vln), (exc, hv, hr, hvp) in flags.items():
        vl = bpy.data.scenes[scn].view_layers[vln]
        def find(lc):
            if lc.collection == coll:
                return lc
            for ch in lc.children:
                r = find(ch)
                if r: return r
        lc = find(vl.layer_collection)
        if lc:
            lc.exclude = exc
            if not exc:
                lc.hide_viewport = hv


def is_hidden(flags):
    return any(v[0] or v[2] for v in flags.values())


# ---------------------------------------------------------------- structure helpers
def parents_of(coll):
    ps = [c for c in bpy.data.collections if not c.library and coll.name in c.children and c.children[coll.name] == coll]
    ps += [s.collection for s in bpy.data.scenes if coll.name in s.collection.children and s.collection.children[coll.name] == coll]
    return ps


def descendants(o):
    return [o] + list(o.children_recursive)


def keep_local_objects(coll):
    """Cameras/lights (and their track targets) stay in the scene file."""
    keep = set()
    for o in coll.all_objects:
        if o.type in ('CAMERA', 'LIGHT'):
            keep.add(o)
            for con in o.constraints:
                t = getattr(con, 'target', None)
                if t is not None and t in set(coll.all_objects):
                    keep.add(t)
    return keep


def split_out_local(coll, scene_parent=None):
    keep = keep_local_objects(coll)
    if not keep:
        return None
    name = coll.name + '_cams'
    lc = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    (scene_parent or bpy.context.scene.collection).children.link(lc) if lc.name not in (scene_parent or bpy.context.scene.collection).children else None
    for o in keep:
        for c in list(o.users_collection):
            if c == coll or c in set(coll.children_recursive):
                c.objects.unlink(o)
        if lc not in o.users_collection:
            lc.objects.link(o)
    log('kept local', name, [o.name for o in keep])
    return lc


def make_root(coll, root_name, at_obj=None):
    """Give a collection of loose objects a single root empty (transforms preserved)."""
    roots = [o for o in coll.objects if o.parent is None or o.parent not in set(coll.all_objects)]
    loc = (at_obj.matrix_world.translation.copy() if at_obj else roots[0].matrix_world.translation.copy())
    e = bpy.data.objects.new(root_name, None)
    e.empty_display_size = 0.5
    coll.objects.link(e)
    e.matrix_world = Matrix.Translation(loc)
    bpy.context.view_layer.update()
    for o in roots:
        mw = o.matrix_world.copy(); o.parent = e; o.matrix_world = mw
    bpy.context.view_layer.update()
    return e


def collection_from_roots(parent_coll, root_names, new_name_fn, dest_parent=None):
    """Move each root (+ all descendants) out of parent_coll into its own new collection,
    created under dest_parent (default: parent_coll)."""
    out = []
    dest_parent = dest_parent or parent_coll
    for rn in root_names:
        r = bpy.data.objects[rn]
        nc = bpy.data.collections.new(new_name_fn(rn))
        dest_parent.children.link(nc)
        for o in descendants(r):
            for c in list(o.users_collection):
                if c == parent_coll:
                    c.objects.unlink(o)
            nc.objects.link(o)
        out.append((nc, r))
    return out


# ---------------------------------------------------------------- write / link
def write_lib(relpath, ids, mark_asset=True):
    path = os.path.join(REPO, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for i in ids:
        if mark_asset and isinstance(i, bpy.types.Collection) and i.asset_data is None:
            try:
                i.asset_mark()
            except Exception as e:
                warn('asset_mark failed', i.name, e)
    bpy.data.libraries.write(path, set(ids), path_remap='RELATIVE_ALL', fake_user=True, compress=True)
    REPORT['written'].append((relpath, [i.name for i in ids], os.path.getsize(path)))
    log('wrote', relpath, round(os.path.getsize(path) / 1e6, 2), 'MB', [i.name for i in ids])
    return path


def link_colls(relpath, names):
    path = os.path.join(REPO, relpath)
    with bpy.data.libraries.load(path, link=True, relative=True) as (src, dst):
        missing = [n for n in names if n not in src.collections]
        if missing:
            raise RuntimeError(f'{relpath} lacks {missing}')
        dst.collections = list(names)
    REPORT['linked'].append((relpath, names))
    return dict(zip(names, dst.collections))


def delete_local(colls, keep=()):
    allc = set()
    for c in colls:
        allc.add(c); allc |= set(c.children_recursive)
    objs = set()
    for c in allc:
        objs |= set(o for o in c.all_objects if not o.library)
    for o in list(objs):
        if o in keep:
            continue
        other = [c for c in o.users_collection if c not in allc]
        if other:
            warn('object also in other collections, kept local:', o.name, [c.name for c in other])
            continue
        bpy.data.objects.remove(o, do_unlink=True)
    for c in sorted(allc, key=lambda c: -len(c.children_recursive)):
        if not c.library and c.name in bpy.data.collections:
            bpy.data.collections.remove(c)


def purge():
    for _ in range(3):
        bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


def extract(relpath, names):
    """World-coordinate extraction: write collections, link them back in place."""
    colls = [bpy.data.collections[n] for n in names]
    for c in colls:
        split_out_local(c)
    flags = {c.name: layer_flags(c) for c in colls}
    write_lib(relpath, colls)
    linked = link_colls(relpath, names)
    for c in colls:
        c.user_remap(linked[c.name])
    delete_local(colls)
    for n, l in linked.items():
        apply_layer_flags(l, flags[n])
    return linked


def extract_normalized(relpath, specs):
    """specs: list of (collection_name, root_object_name). Root goes to origin in the library;
    the scene gets an instance empty with the root's old world matrix."""
    items = []
    for cn, rn in specs:
        c = bpy.data.collections[cn]; r = bpy.data.objects[rn]
        if r.parent is not None:
            warn('root has parent', rn, r.parent.name)
        W = r.matrix_world.copy()
        flags = layer_flags(c)
        parents = parents_of(c)
        hide_r, hide_v = r.hide_render, r.hide_viewport
        r.matrix_world = Matrix.Identity(4)
        items.append((c, r, W, flags, parents, hide_r, hide_v))
    bpy.context.view_layer.update()
    write_lib(relpath, [i[0] for i in items])
    linked = link_colls(relpath, [i[0].name for i in items])
    for c, r, W, flags, parents, hide_r, hide_v in items:
        l = linked[c.name]
        # existing instancers of this collection expected the root at its old place
        for o in bpy.data.objects:
            if not o.library and o.instance_type == 'COLLECTION' and o.instance_collection == c:
                o.instance_collection = l
                o.matrix_world = o.matrix_world @ W
        placed = [p for p in parents if not p.name.startswith('_')]
        for p in parents:
            p.children.unlink(c)
        if placed:
            e = bpy.data.objects.new(c.name + '_inst', None)
            e.instance_type = 'COLLECTION'; e.instance_collection = l
            e.empty_display_size = 1.0
            e.matrix_world = W
            e.hide_render = hide_r or is_hidden(flags)
            e.hide_viewport = hide_v or is_hidden(flags)
            for p in placed:
                p.objects.link(e)
        else:
            # prototype libraries (_AssetLib etc.) keep the linked collection as a child
            for p in parents:
                p.children.link(l)
                apply_layer_flags(l, flags)
        c.user_remap(l)
    delete_local([i[0] for i in items])
    return linked


# ---------------------------------------------------------------- comparison / relink
def _base(n):
    return re.sub(r'\.\d{3}$', '', n)


def world(o):
    """matrix_world from the parent chain (linked objects outside a scene are not evaluated)."""
    if o.parent is None:
        return o.matrix_basis.copy()
    return world(o.parent) @ o.matrix_parent_inverse @ o.matrix_basis


def signature(coll, root=None):
    """Name-independent fingerprint: per object type, vertex count and the mesh's
    bounds relative to the root (object names get renumbered between files, and
    bound_box is not evaluated for linked data, so vertices are read directly)."""
    import numpy as np
    inv = world(root).inverted() if root else Matrix.Identity(4)
    sig = []
    for o in coll.all_objects:
        M = inv @ world(o)
        if o.type == 'MESH' and len(o.data.vertices):
            co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get('co', co)
            co = co.reshape(-1, 3)
            m = np.array(M)
            w = co @ m[:3, :3].T + m[:3, 3]
            b = tuple(np.round(w.min(0), 2)) + tuple(np.round(w.max(0), 2))
            sig.append(('MESH', len(co)) + tuple(float(x) for x in b))
        else:
            t = M.translation
            sig.append((o.type, 0, round(t.x, 2), round(t.y, 2), round(t.z, 2)))
    return sorted(sig)


def relink(relpath, mapping, roots=None):
    """mapping {local_collection: library_collection}. Remaps only collections whose
    signature matches the library copy; returns the names that did not match."""
    linked = link_colls(relpath, list(mapping.values()))
    bad = []
    for ln, libn in mapping.items():
        c = bpy.data.collections[ln]; l = linked[libn]
        r_loc = bpy.data.objects.get(roots[ln]) if roots else None
        r_lib = None
        if roots:
            r_lib = next((o for o in l.all_objects if _base(o.name) == _base(roots[ln])), None)
        if signature(c, r_loc) != signature(l, r_lib):
            bad.append(ln); REPORT['mismatch'].append((ln, relpath, libn))
            warn('signature mismatch', ln, 'vs', relpath, libn)
            continue
        flags = layer_flags(c)
        c.user_remap(l)
        delete_local([c])
        apply_layer_flags(l, flags)
        log('relinked', ln, '->', relpath, libn)
    for l in linked.values():
        if l.users == 0 or (l.users == 1 and l.use_fake_user):
            pass
    return bad


def finish(scene_relpath, report_relpath=None):
    purge()
    path = os.path.join(REPO, scene_relpath)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True, relative_remap=True)
    # verify that every library and image resolves
    for lib in bpy.data.libraries:
        if not os.path.exists(bpy.path.abspath(lib.filepath)):
            REPORT['missing'].append(('library', lib.filepath))
    for img in bpy.data.images:
        if img.packed_file or img.source in ('VIEWER', 'GENERATED') or not img.filepath:
            continue
        if not os.path.exists(bpy.path.abspath(img.filepath, library=img.library)):
            REPORT['missing'].append(('image', img.name, img.filepath))
    REPORT['scene'] = (scene_relpath, os.path.getsize(path))
    if report_relpath:
        with open(os.path.join(REPO, report_relpath), 'w') as f:
            json.dump(REPORT, f, indent=1, default=str)
    log('saved', scene_relpath, round(os.path.getsize(path) / 1e6, 2), 'MB; missing:', REPORT['missing'])


def relink_normalized(relpath, cn, rn, libcn=None):
    """Replace a scene-placed collection by an instance of an existing library asset,
    if the two match (signature relative to their roots). Returns True on success."""
    libcn = libcn or cn
    c = bpy.data.collections[cn]; r = bpy.data.objects[rn]
    l = link_colls(relpath, [libcn])[libcn]
    r_lib = next((o for o in l.all_objects if _base(o.name) == _base(rn)), None)
    if r_lib is None or signature(c, r) != signature(l, r_lib):
        REPORT['mismatch'].append((cn, relpath, libcn)); warn('normalized mismatch', cn, relpath, libcn)
        return False
    W = r.matrix_world @ r_lib.matrix_world.inverted()
    flags = layer_flags(c); parents = parents_of(c)
    for p in parents:
        p.children.unlink(c)
    placed = [p for p in parents if not p.name.startswith('_')]
    if placed:
        e = bpy.data.objects.new(libcn + '_inst', None)
        e.instance_type = 'COLLECTION'; e.instance_collection = l
        e.matrix_world = W
        e.hide_render = r.hide_render or is_hidden(flags)
        e.hide_viewport = r.hide_viewport or is_hidden(flags)
        for p in placed:
            p.objects.link(e)
    for o in bpy.data.objects:
        if not o.library and o.instance_type == 'COLLECTION' and o.instance_collection == c:
            o.instance_collection = l
            o.matrix_world = o.matrix_world @ r.matrix_world @ r_lib.matrix_world.inverted()
    c.user_remap(l)
    delete_local([c])
    log('relinked (normalized)', cn, '->', relpath, libcn)
    return True


def rename_collections(mapping):
    for a, b in mapping.items():
        if a in bpy.data.collections:
            bpy.data.collections[a].name = b
