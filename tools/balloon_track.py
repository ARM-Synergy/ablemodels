"""Print world positions of the balloon-launch parts over the animation (for before/after checks)."""
import bpy, json, sys
out = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene
names = ('Balloon', 'Sonde', 'BalloonLine', 'Launcher_Hold', 'Launcher_Release', 'Helper_Hold', 'Helper_Release')
res = {}
for f in (1, 60, 120, 180, 240, 300, 360, 480):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    for inst in dg.object_instances:
        n = inst.object.name.split('.')[0]
        if n in names and inst.show_self:
            m = inst.matrix_world
            res[f'{f}:{n}'] = [round(v, 3) for v in list(m.translation) + list(m.col[2][:3])]
json.dump(res, open(out, 'w'), indent=0, sort_keys=True)
