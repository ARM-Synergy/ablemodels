"""Move the M1 radiosonde balloon launch (balloon, sonde, line and launch crew) out of
scenes/M1/M1.blend into instruments/BALLOON/BALLOON.blend and link it back.
blender -b scenes/M1/M1.blend --python tools/build_balloon.py

All parts are parented to a new root at the launch point (transforms and the
release animation preserved), the root is moved to the origin in the library,
and M1 gets a collection instance at the original launch point.
"""
import bpy, os, sys
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ablib as A
D = bpy.data
c = D.collections['BalloonLaunch']
c.name = 'INST_BALLOON'
crew = D.collections['BalloonCrew']
crew.name = 'BALLOON_Crew'

sonde = D.objects['Sonde']
root = D.objects.new('BALLOON_root', None)
root.empty_display_size = 1.0
c.objects.link(root)
root.matrix_world = Matrix.Translation(Vector((sonde.matrix_world.translation.x,
                                               sonde.matrix_world.translation.y, -0.08)))
bpy.context.view_layer.update()
inv = root.matrix_world.inverted()
for o in list(c.all_objects):
    if o is root or o.parent is not None:
        continue
    o.parent = root
    o.matrix_parent_inverse = inv      # keeps world placement and the keyframed motion
bpy.context.view_layer.update()

A.extract_normalized('instruments/BALLOON/BALLOON.blend', [('INST_BALLOON', 'BALLOON_root')])
A.purge()
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_mainfile(compress=True, relative_remap=True)
print('BALLOON_DONE')
