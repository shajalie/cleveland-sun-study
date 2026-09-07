"""Incremental equivalent of scene.py's pool excavation, for existing scenes."""
import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(P/'cleveland-daylight.blend'))
context=bpy.data.objects.get('Context ground')
for v in context.data.vertices:
 if v.co.x<-50:v.co.x=-2000
 if v.co.x>80:v.co.x=2000
 if v.co.y<-30:v.co.y=-2000
 if v.co.y>70:v.co.y=2000
water=bpy.data.objects.get('Pool water | no access');cut=water.copy();cut.data=water.data.copy();bpy.context.collection.objects.link(cut);cut.name='Pool excavation cutter'
for v in cut.data.vertices:v.co.z=.12 if v.co.z>.03 else -1.88
for name in ['Property ground','Context ground','Pool deck / surround']:
 ob=bpy.data.objects.get(name);mod=ob.modifiers.new('Pool excavation','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cut,do_unlink=True)
for v in water.data.vertices:
 if v.co.z<.03:v.co.z=-.65
# Restore standard export graph, then the reference renderer reinstates its
# documented architectural shadow approximation after this export.
for m in bpy.data.materials:
 if m.name.startswith('Glazing'):
  nt=m.node_tree;nt.links.new(nt.nodes.get('Principled BSDF').outputs[0],nt.nodes.get('Material Output').inputs['Surface'])
for ob in list(bpy.context.scene.objects):
 if ob.name.startswith('Validation sealed room'):bpy.data.objects.remove(ob,do_unlink=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'cleveland-daylight.blend'))
bpy.ops.export_scene.gltf(filepath=str(P/'public/house.glb'),export_format='GLB',export_extras=True,export_cameras=False,export_lights=False)
print('POOL_FIXED')
