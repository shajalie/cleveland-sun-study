import bpy, math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(P/'cleveland-daylight.blend'));s=bpy.context.scene
for o in s.objects:
 if o.type=='MESH':o.hide_render=True
s.cycles.samples=8;s.cycles.device='CPU';s.render.resolution_x=32;s.render.resolution_y=32;s.view_settings.view_transform='Standard';s.view_settings.exposure=0
for name,d in [('zenith',(0,0,1)),('nadir',(0,0,-1))]:
 s.camera.location=(0,0,100);s.camera.rotation_euler=Vector(d).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
