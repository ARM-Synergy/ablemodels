"""Procedural builder helpers for new instrument assets (instruments/<NAME>/<NAME>.blend).

Run the per-instrument scripts headless from the repository root:
    blender -b --factory-startup --python tools/build_inst_<name>.py

Conventions follow the extracted instrument library:
  * one collection INST_<NAME>, marked as an asset, not linked to any scene;
  * a root empty <NAME>_root at the origin (ARROWS, 0.5) that parents every part and
    carries the custom properties instrument / full_name / sites / sources / notes /
    height_m / bbox_min / bbox_max (lists stored as JSON strings);
  * +Z up, +Y north, metres; the asset stands on z = 0.
Materials are appended (copied, never linked) from existing instrument files so new
assets share the library's PBR look; their textures stay relative
(//../../textures/pbr/...). Source files are only read.
"""
import bpy, bmesh, math, os, json
from mathutils import Vector, Matrix

REPO = os.environ.get('ABLE_REPO') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT_SOURCES = ['instruments/MET/MET.blend', 'instruments/SIRS/SIRS.blend',
               'instruments/LDIS/LDIS.blend', 'instruments/ASI/ASI.blend']
# simple materials (no textures) used when the library has nothing suitable
FLAT = {
    'soil_dark': ((0.11, 0.08, 0.055), 0.0, 0.95),
    'soil_fresh': ((0.17, 0.12, 0.08), 0.0, 0.9),
    'orange_flag': ((0.95, 0.30, 0.02), 0.0, 0.5),
    'radar_white': ((0.86, 0.87, 0.86), 0.0, 0.45),
    'solar_cell': ((0.02, 0.03, 0.07), 0.3, 0.15),
    'metek_grey': ((0.55, 0.57, 0.58), 0.0, 0.4),
    'stardot_grey': ((0.62, 0.63, 0.62), 0.2, 0.35),
    'kipp_white': ((0.88, 0.88, 0.86), 0.0, 0.35),
    'teros_blue': ((0.05, 0.18, 0.45), 0.0, 0.4),
}
_mat_index = None
_mats = {}


def log(*a):
    print('[inst]', *a, flush=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    global _mat_index
    _mat_index = None
    _mats.clear()


def _index():
    global _mat_index
    if _mat_index is None:
        _mat_index = {}
        for rel in MAT_SOURCES:
            p = os.path.join(REPO, rel)
            with bpy.data.libraries.load(p, link=False) as (src, _):
                names = list(src.materials)
            for n in names:
                _mat_index.setdefault(n.split('.')[0], (p, n))
    return _mat_index


def mat(base):
    """Material by base name: appended from the library, else a flat Principled one."""
    if base in _mats:
        return _mats[base]
    idx = _index()
    if base in idx:
        p, n = idx[base]
        with bpy.data.libraries.load(p, link=False) as (_, dst):
            dst.materials = [n]
        m = dst.materials[0]
        m.name = base
    else:
        col, metal, rough = FLAT[base]
        m = bpy.data.materials.new(base)
        m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*col, 1)
        b.inputs['Metallic'].default_value = metal
        b.inputs['Roughness'].default_value = rough
    _mats[base] = m
    return m


def frame_z(p0, p1):
    """Matrix whose +Z runs from p0 towards p1, origin at p0."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = d.normalized().to_track_quat('Z', 'Y' if abs(d.normalized().z) < 0.99 else 'X')
    return Matrix.Translation(p0) @ q.to_matrix().to_4x4(), d.length


class MB:
    """bmesh accumulator: primitives in world (asset) coordinates, per-face materials."""

    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []

    def _mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def _tag(self, geom, m, smooth):
        mi = self._mi(m)
        faces = set()
        for v in geom:
            if isinstance(v, bmesh.types.BMVert):
                faces.update(v.link_faces)
            elif isinstance(v, bmesh.types.BMFace):
                faces.add(v)
        for f in faces:
            f.material_index = mi
            f.smooth = smooth
        return faces

    def box(self, c, size, m, rot=None):
        M = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot is not None else Matrix()) \
            @ Matrix.Diagonal((*size, 1))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        self._tag(r['verts'], m, False)

    def beam(self, p0, p1, w, h, m):
        M, L = frame_z(p0, p1)
        M = M @ Matrix.Translation((0, 0, L / 2)) @ Matrix.Diagonal((w, h, L, 1))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        self._tag(r['verts'], m, False)

    def cyl(self, p0, p1, r0, m, r1=None, seg=24, cap=True, smooth=True):
        M, L = frame_z(p0, p1)
        M = M @ Matrix.Translation((0, 0, L / 2))
        r = bmesh.ops.create_cone(self.bm, cap_ends=cap, cap_tris=False, segments=seg,
                                  radius1=r0, radius2=r0 if r1 is None else r1, depth=L, matrix=M)
        faces = self._tag(r['verts'], m, smooth)
        for f in faces:                      # keep caps flat-shaded
            if len(f.verts) > 4:
                f.smooth = False

    def sphere(self, c, r, m, seg=16, scale=(1, 1, 1)):
        M = Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*scale, 1))
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=max(6, seg // 2),
                                        radius=r, matrix=M)
        self._tag(res['verts'], m, True)

    def lathe(self, prof, m, M=Matrix(), seg=32, smooth=True):
        """prof: [(r, z), ...] revolved about local Z; M places it."""
        rings = []
        for (r, z) in prof:
            ring = []
            for i in range(seg):
                a = 2 * math.pi * i / seg
                ring.append(self.bm.verts.new(M @ Vector((r * math.cos(a), r * math.sin(a), z))))
            rings.append(ring)
        new = []
        for a, b in zip(rings, rings[1:]):
            for i in range(seg):
                j = (i + 1) % seg
                new.append(self.bm.faces.new((a[i], a[j], b[j], b[i])))
        if prof[0][0] > 1e-6:
            new.append(self.bm.faces.new(list(reversed(rings[0]))))
        if prof[-1][0] > 1e-6:
            new.append(self.bm.faces.new(rings[-1]))
        self._tag(new, m, smooth)
        for f in new:
            if len(f.verts) > 4:
                f.smooth = False

    def grid(self, pts, m, smooth=True, close_u=False):
        """pts[i][j] -> quads; close_u wraps index j."""
        vs = [[self.bm.verts.new(Vector(p)) for p in row] for row in pts]
        new = []
        nj = len(vs[0])
        for i in range(len(vs) - 1):
            for j in range(nj if close_u else nj - 1):
                k = (j + 1) % nj
                new.append(self.bm.faces.new((vs[i][j], vs[i][k], vs[i + 1][k], vs[i + 1][j])))
        self._tag(new, m, smooth)
        return vs

    def obj(self, name, coll, parent):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for mm in self.mats:
            me.materials.append(mat(mm))
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        o.parent = parent
        return o


def part(name, coll, parent, build):
    """build(mb) fills a fresh MB; returns the object."""
    mb = MB()
    build(mb)
    return mb.obj(name, coll, parent)


def cable(name, pts, r, coll, parent, m='cable'):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = 2
    sp = cu.splines.new('NURBS')
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (*q, 1)
    sp.use_endpoint_u = True
    sp.order_u = min(4, len(pts))
    sp.resolution_u = 8
    cu.materials.append(mat(m))
    o = bpy.data.objects.new(name, cu)
    coll.objects.link(o)
    o.parent = parent
    return o


def wire(name, p0, p1, r, coll, parent, m='galvanized'):
    """Straight guy wire / stay as a thin cylinder."""
    return part(name, coll, parent, lambda mb: mb.cyl(p0, p1, r, m, seg=6))


def empty(name, coll, parent, loc=(0, 0, 0), size=0.2):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = size
    e.location = loc
    coll.objects.link(e)
    e.parent = parent
    return e


def start(name):
    """New INST_<name> collection + <name>_root."""
    reset()
    coll = bpy.data.collections.new('INST_' + name)
    root = bpy.data.objects.new(name + '_root', None)
    root.empty_display_type = 'ARROWS'
    root.empty_display_size = 0.5
    coll.objects.link(root)
    return coll, root


def below(coll):
    """Child collection for geometry below grade (probes, footings, buried cable).
    Hidden in viewport and render so scenes, previews and bounds see only what stands on
    the ground; un-hide it for cut-away views."""
    nm = coll.name.replace('INST_', '') + '_BelowGrade'
    c = bpy.data.collections.get(nm)
    if c is None:
        c = bpy.data.collections.new(nm)
        coll.children.link(c)
        c.hide_viewport = True
        c.hide_render = True
    return c


def finish(name, coll, root, full_name, sites, sources, notes):
    """Write props + bbox, mark asset, save instruments/<name>/<name>.blend."""
    sc = bpy.data.scenes[0] if bpy.data.scenes else bpy.data.scenes.new('Scene')
    sc.collection.children.link(coll)
    # drop anything an append dragged in that is not part of the asset (e.g. old parents)
    keep = set(coll.all_objects)
    for o in list(bpy.data.objects):
        if o not in keep:
            log('drop stray', o.name)
            bpy.data.objects.remove(o)
    # bake curve cables to meshes: an instanced curve reports a stale unit-cube bound_box,
    # which drops tools/render_previews.py's ground plane to z = -1
    for c in [coll] + list(coll.children_recursive):
        c.hide_viewport = False             # evaluate hidden below-grade parts too
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    for o in [o for o in coll.all_objects if o.type == 'CURVE']:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        me.name = o.name
        new = bpy.data.objects.new(o.name + '_m', me)
        new.parent = o.parent
        new.matrix_parent_inverse = o.matrix_parent_inverse.copy()
        new.matrix_basis = o.matrix_basis.copy()
        for c in o.users_collection:
            c.objects.link(new)
        nm = o.name
        cu = o.data
        bpy.data.objects.remove(o)
        bpy.data.curves.remove(cu)
        new.name = nm
    bgc = bpy.data.collections.get(name + '_BelowGrade')
    if bgc is not None:
        bgc.hide_viewport = True
    bpy.data.orphans_purge(do_recursive=True)
    # evaluate in a temporary scene so modifiers/curves count
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bg = bpy.data.collections.get(name + '_BelowGrade')
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3); zbg = 0.0
    for o in coll.all_objects:
        if o.type not in ('MESH', 'CURVE'):
            continue
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()                    # curve bound_box is stale; use real vertices
        for v in me.vertices:
            w = o.matrix_world @ v.co
            if bg is not None and bg in o.users_collection:
                zbg = min(zbg, w.z)          # bbox describes what stands above ground
                continue
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
        oe.to_mesh_clear()
    if bg is not None:
        root['below_grade_m'] = round(zbg, 3)
        root['below_grade_collection'] = bg.name
    root['instrument'] = name
    root['full_name'] = full_name
    root['sites'] = json.dumps(sites)
    root['sources'] = json.dumps(sources)
    root['notes'] = notes
    root['height_m'] = round(hi.z, 3)
    root['bbox_min'] = json.dumps([round(v, 3) for v in lo])
    root['bbox_max'] = json.dumps([round(v, 3) for v in hi])
    sc.collection.children.unlink(coll)
    coll.asset_mark()
    out = os.path.join(REPO, 'instruments', name, name + '.blend')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    bpy.ops.file.make_paths_relative()
    for img in bpy.data.images:          # all textures must resolve inside the repo
        ap = bpy.path.abspath(img.filepath)
        assert os.path.exists(ap), ('missing texture', img.filepath)
        assert img.filepath.startswith('//'), ('absolute texture path', img.filepath)
    bpy.ops.wm.save_mainfile(compress=True)
    nobj = len(coll.all_objects)
    log('SAVED', out, nobj, 'objects, height', root['height_m'], 'bbox', root['bbox_min'], root['bbox_max'])
    return out
