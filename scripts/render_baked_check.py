import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(P/'cleveland-bake.blend'));s=bpy.context.scene
if '--joined' in sys.argv:
 for group in ['interior','exterior']:
  objects=[o for o in s.objects if o.type=='MESH' and o.get('lightmap_group')==group];bpy.ops.object.select_all(action='DESELECT')
  for o in objects:o.select_set(True)
  bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
c=next(x for x in json.loads((P/'public/lightmaps/manifest.json').read_text()) if x['key']=='2026-09-22-780-clear')
materials={}
for o in s.objects:
 group=o.get('lightmap_group')
 if not group or o.type!='MESH':continue
 for slot in o.material_slots:
  original=slot.material;key=(original.name,group)
  if key not in materials:
   m=original.copy();nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF');out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
   uv=nodes.new('ShaderNodeUVMap');uv.uv_map='Lightmap';tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P/'public'/c['maps'][group].lstrip('/')),check_existing=True);tex.image.colorspace_settings.name='Non-Color';links.new(uv.outputs[0],tex.inputs[0])
   mul=nodes.new('ShaderNodeVectorMath');mul.operation='SCALE';links.new(tex.outputs['Color'],mul.inputs[0]);links.new(tex.outputs['Alpha'],mul.inputs[3]);mul2=nodes.new('ShaderNodeVectorMath');mul2.operation='SCALE';links.new(mul.outputs[0],mul2.inputs[0]);mul2.inputs[3].default_value=c['ranges'][group]
   color=nodes.new('ShaderNodeVectorMath');color.operation='MULTIPLY';links.new(mul2.outputs[0],color.inputs[0]);color.inputs[1].default_value=bs.inputs['Base Color'].default_value[:3]
   if bs.inputs['Base Color'].is_linked:links.new(bs.inputs['Base Color'].links[0].from_socket,color.inputs[1])
   emit=nodes.new('ShaderNodeEmission');links.new(color.outputs[0],emit.inputs[0]);links.new(emit.outputs[0],out.inputs['Surface']);materials[key]=m
  slot.material=materials[key]
s.render.engine='CYCLES';s.cycles.samples=8;s.cycles.device='GPU';s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
s.render.resolution_x=800;s.render.resolution_y=600;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=3
s.camera.location=(14.55,19.5,2.42);s.camera.rotation_euler=(Vector((14.55,24.5,1.969))-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.lens=23.38
s.render.filepath=str(P/'evidence/baked-blender-check.png');bpy.ops.render.render(write_still=True)
