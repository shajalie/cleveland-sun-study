"""Render matching reference views and enclosed-room / bounce checks in Cycles."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(P/'cleveland-daylight.blend'));scene=bpy.context.scene
for ob in list(scene.objects):
 if ob.type=='LIGHT' or ob.name.startswith('Validation sealed room'):bpy.data.objects.remove(ob,do_unlink=True)
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
# Explicit shared photographic display curve: sRGB(8 L / (1 + 8 L)).
# Three's ReinhardToneMapping uses this identical per-channel expression.
scene.use_nodes=True;nt=scene.node_tree;nt.nodes.clear();rl=nt.nodes.new('CompositorNodeRLayers');exp=nt.nodes.new('CompositorNodeExposure');exp.inputs['Exposure'].default_value=3;nt.links.new(rl.outputs['Image'],exp.inputs['Image']);sep=nt.nodes.new('CompositorNodeSepRGBA');nt.links.new(exp.outputs[0],sep.inputs[0]);comb=nt.nodes.new('CompositorNodeCombRGBA');comb.inputs['A'].default_value=1
for channel in ['R','G','B']:
 add=nt.nodes.new('CompositorNodeMath');add.operation='ADD';add.inputs[1].default_value=1;nt.links.new(sep.outputs[channel],add.inputs[0]);div=nt.nodes.new('CompositorNodeMath');div.operation='DIVIDE';nt.links.new(sep.outputs[channel],div.inputs[0]);nt.links.new(add.outputs[0],div.inputs[1]);nt.links.new(div.outputs[0],comb.inputs[channel])
comp=nt.nodes.new('CompositorNodeComposite');nt.links.new(comb.outputs[0],comp.inputs[0])
case=next(s for s in json.loads((P/'public/skies/manifest.json').read_text())if s['date']=='2026-09-22'and s['time']==780)
def glass_transmission(t):
 for m in bpy.data.materials:
  if not m.name.startswith('Glazing'):continue
  nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*([math.sqrt(t/(.96*.96))]*3),1);bs.inputs['Alpha'].default_value=1
  # Thin parallel architectural glass has negligible shadow displacement.
  # Shadow rays use attenuating straight-through transmission to avoid noisy
  # refractive caustic sampling; visible/reflected paths use dielectric refraction.
  shadow=nt.nodes.get('Architectural shadow')
  if not shadow:
   shadow=nt.nodes.new('ShaderNodeBsdfTransparent');shadow.name='Architectural shadow';lp=nt.nodes.new('ShaderNodeLightPath');mix=nt.nodes.new('ShaderNodeMixShader');nt.links.new(lp.outputs['Is Shadow Ray'],mix.inputs[0]);nt.links.new(bs.outputs[0],mix.inputs[1]);nt.links.new(shadow.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],nt.nodes.get('Material Output').inputs['Surface'])
  shadow.inputs[0].default_value=(*([math.sqrt(t)]*3),1)
  mix=next(n for n in nt.nodes if n.type=='MIX_SHADER');nt.links.new(mix.outputs[0],nt.nodes.get('Material Output').inputs['Surface'])
glass_transmission(.82)
def sky(kind):
 import numpy as np
 nodes=scene.world.node_tree.nodes;links=scene.world.node_tree.links;nodes.clear()
 if kind=='clear':
  im=bpy.data.images.load(str(P/'public'/case['hdr'].lstrip('/')),check_existing=True)
 else:
  w,h=256,256;pixels=np.zeros((h,w,4),dtype=np.float32);pixels[:,:,3]=1
  for y in range(h):
   up=math.cos((1-y/h)*math.pi);v=case['overcast_zenith']*(1+2*up)/3 if up>0 else 0;pixels[y,:,:3]=v
  im=bpy.data.images.new('Shared CIE overcast',width=w,height=h,float_buffer=True);im.pixels.foreach_set(pixels.ravel());im.pack()
 env=nodes.new('ShaderNodeTexEnvironment');env.image=im;bg=nodes.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=1;links.new(env.outputs['Color'],bg.inputs['Color']);out=nodes.new('ShaderNodeOutputWorld');links.new(bg.outputs[0],out.inputs[0])
cam=scene.camera;cam.data.type='PERSP';cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=24/(2*math.tan(math.radians(60)/2))
scene.render.resolution_x=900;scene.render.resolution_y=700;scene.cycles.samples=512;scene.cycles.adaptive_threshold=.01;scene.cycles.transparent_max_bounces=24;scene.render.image_settings.file_format='PNG'
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for dev in prefs.devices:dev.use=dev.type=='OPTIX'
 scene.cycles.device='GPU' if any(d.type=='OPTIX' for d in prefs.devices) else 'CPU'
except:scene.cycles.device='CPU'
out=P/'public/references';out.mkdir(exist_ok=True)
def view(x,y,z,yaw=0,pitch=-.09):
 cam.location=(x,y,z);direction=Vector((math.sin(yaw)*math.cos(pitch),math.cos(yaw)*math.cos(pitch),math.sin(pitch)));cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
def render(name):
 scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 print('RENDER_COMPLETE',name,flush=True)
if '--bath-check' in sys.argv:
 sky('clear');view(14.2,20.8,5.57,math.pi/2,-.09);scene.cycles.samples=64;scene.render.resolution_x=450;scene.render.resolution_y=350;render('bath-intrusion-check');sys.exit(0)
if '--pool-check' in sys.argv:
 sky('clear');view(10.6,35.9,1.636,-2.1,-.35);render('pool-clear');bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'cleveland-daylight.blend'));sys.exit(0)
for name,kind,pos,yaw,pitch in [('study-clear','clear',(14.55,19.5,2.42),0,-.09),('study-overcast','overcast',(14.55,19.5,2.42),0,-.09),('sunroom-clear','clear',(5.7,23.3,5.57),0,-.09),('yard-clear','clear',(10.8,34,1.636),math.pi,-.06),('pool-clear','clear',(10.6,35.9,1.636),-2.1,-.35),('bath-clear','clear',(14.2,20.8,5.57),math.pi/2,-.09)]:
 sky(kind);view(*pos,yaw,pitch);render(name)
# Paired low-bounce render identifies the contribution from indirect paths.
sky('overcast');view(14.55,19.5,2.42);scene.cycles.diffuse_bounces=0;render('study-overcast-no-bounce');scene.cycles.diffuse_bounces=12
# Material sensitivity checks, keeping exposure, sky and camera fixed.
glass_transmission(.55)
render('study-overcast-dark-glass')
glass_transmission(.82)
for m in bpy.data.materials:
 if m.name.startswith('Plaster'):
  bs=m.node_tree.nodes.get('Principled BSDF')
  for link in list(bs.inputs['Base Color'].links):m.node_tree.links.remove(link)
  bs.inputs['Base Color'].default_value=(.30,.29,.27,1)
render('study-overcast-dark-walls')
for m in bpy.data.materials:
 if m.name.startswith('Plaster'):
  bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.72,.70,.65,1);tex=next(n for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image.name=='plaster.png');m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
# Fully sealed opaque room has no artificial fill: it must remain black.
for ob in list(scene.objects):
 if ob.type=='MESH':ob.hide_render=True
bpy.ops.mesh.primitive_cube_add(size=6,location=(0,0,3));cube=bpy.context.object;cube.name='Validation sealed room';m=bpy.data.materials.new('Opaque gray test');m.diffuse_color=(.5,.5,.5,1);cube.data.materials.append(m);view(0,0,2);render('sealed-room')
cube.hide_render=True
for ob in list(scene.objects):
 if ob.type=='MESH'and ob!=cube:ob.hide_render=False
sky('clear');view(14.55,19.5,2.42);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'cleveland-daylight.blend'))
