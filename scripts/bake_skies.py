"""Bake Nishita atmospheric transport once; share linear HDR pixels in both renderers.
The finite solar disk is part of the HDR. Never add a second Sun in appearance mode.
"""
import bpy, math, json, numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1];out=P/'public/skies';out.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=4;s.cycles.use_denoising=False
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type=='OPTIX'
 s.cycles.device='GPU'
except:pass
s.render.resolution_x=4096;s.render.resolution_y=2048;s.render.resolution_percentage=100
s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_depth='32';s.render.image_settings.color_mode='RGB';s.view_settings.view_transform='Standard';s.use_nodes=False
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='PANO';cam.data.panorama_type='EQUIRECTANGULAR';cam.rotation_euler=Vector((1,0,0)).to_track_quat('-Z','Y').to_euler();s.camera=cam
world=bpy.data.worlds.new('Nishita atmosphere');world.use_nodes=True;s.world=world;n=world.node_tree.nodes;n.clear();sky=n.new('ShaderNodeTexSky');sky.sky_type='NISHITA';sky.sun_disc=True;sky.sun_size=math.radians(.53);sky.sun_intensity=1;sky.altitude=.09;sky.air_density=1;sky.dust_density=1;sky.ozone_density=1
bg=n.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=1;output=n.new('ShaderNodeOutputWorld');world.node_tree.links.new(sky.outputs[0],bg.inputs[0]);world.node_tree.links.new(bg.outputs[0],output.inputs[0])

def hdr(path,rgb):
 h,w,_=rgb.shape;maxc=rgb.max(axis=2);mant,exp=np.frexp(maxc);factor=np.where(maxc>1e-32,mant*256/np.maximum(maxc,1e-32),0);rgbe=np.zeros((h,w,4),dtype=np.uint8);rgbe[:,:,:3]=np.clip(rgb*factor[:,:,None],0,255).astype(np.uint8);rgbe[:,:,3]=np.where(maxc>1e-32,exp+128,0).astype(np.uint8)
 with path.open('wb') as f:
  f.write(f'#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y {h} +X {w}\n'.encode())
  for row in rgbe:
   f.write(bytes([2,2,w>>8,w&255]))
   for c in range(4):
    a=row[:,c].tobytes();i=0
    while i<w:
     run=1
     while i+run<w and run<127 and a[i+run]==a[i]:run+=1
     if run>=4:f.write(bytes([128+run,a[i]]));i+=run
     else:
      start=i;i+=run
      while i<w and i-start<124:
       run=1
       while i+run<w and run<4 and a[i+run]==a[i]:run+=1
       if run>=4:break
       i+=run
      f.write(bytes([i-start])+a[start:i])

report=[]
for case in json.loads((P/'public/scenarios.json').read_text())[:12]:
 sun=case['sun'];sky.sun_elevation=math.radians(max(-5,sun['alt']));sky.sun_rotation=math.atan2(sun['x'],sun['y']);key=f"{case['date']}-{case['time']}"
 exr=P/'sky-temp.exr';s.render.filepath=str(exr);bpy.ops.render.render(write_still=True);im=bpy.data.images.load(str(exr),check_existing=False);pixels=np.array(im.pixels[:],dtype=np.float32).reshape(2048,4096,4)[::-1,:,:3].copy().reshape(1024,2,2048,2,3).mean(axis=(1,3));bpy.data.images.remove(im)
 # A single global radiance-unit scale, applied equally to every scenario and engine.
 pixels/=30
 # Ground is modeled geometry; a black lower hemisphere prevents subterranean fill.
 pixels[512:]=0
 hdr(out/(key+'.hdr'),pixels)
 lum=pixels@np.array([.2126,.7152,.0722]);iy,ix=np.unravel_index(lum.argmax(),lum.shape);phi=(ix+.5)/2048*2*math.pi-math.pi;alt=math.pi/2-(iy+.5)/1024*math.pi
 direction=np.array([math.cos(alt)*math.cos(phi),-math.cos(alt)*math.sin(phi),math.sin(alt)]);desired=np.array([sun['x'],sun['y'],sun['z']]);err=math.degrees(math.acos(np.clip(direction@desired,-1,1))) if sun['alt']>0 else None
 up=np.cos((np.arange(1024)+.5)/1024*math.pi);solid=2*math.pi/2048*math.pi/1024*np.sin((np.arange(1024)+.5)/1024*math.pi)
 horiz=float((lum*np.maximum(up,0)[:,None]*solid[:,None]).sum())
 # CIE standard overcast shape. Chosen cloudy irradiance is 35% of clear global,
 # an explicit weather scenario, not a local measurement or a sky forecast.
 sky_scale=horiz*.35*9/(7*math.pi)
 report.append({**case,'hdr':f'/skies/{key}.hdr','disk_alignment_error_degrees':err,'clear_horizontal_relative':horiz,'overcast_zenith':sky_scale,'unit_scale':1/30})
 print('SKY_COMPLETE',key,'alignment',err,'horizontal',horiz,'pixel',ix,iy,'direction',direction.tolist(),'desired',desired.tolist(),flush=True)
 if err is not None and err>1:raise RuntimeError('HDR sun orientation mismatch')
(out/'manifest.json').write_text(json.dumps(report,indent=2));exr.unlink(missing_ok=True)
