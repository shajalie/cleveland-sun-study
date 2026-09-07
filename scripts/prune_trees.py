import bpy,json
from mathutils import Vector
from pathlib import Path
P=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(P/'cleveland-daylight.blend'));I=json.loads((P/'model-data.json').read_text())['indoor']
def occupied(x,y,z):
 def inside(p,poly):
  hit=False
  for i,a in enumerate(poly):
   b=poly[i-1]
   if (a[1]>p[1])!=(b[1]>p[1]) and p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:hit=not hit
  return hit
 if z<8.5 and 3.9<x<17.6 and 13.2<y<22.55:return True
 return z<7.4 and any(inside((x+dx,y+dy),f['outline'])for f in I['floors']for dx,dy in [(0,0),(.2,0),(-.2,0),(0,.2),(0,-.2)])

removed=0
for ob in list(bpy.context.scene.objects):
 if ob.type!='MESH':continue
 if ob.get('tree'):
  me=ob.data;vs=[tuple(v.co)for v in me.vertices];faces=[]
  for p in me.polygons:
   if any(occupied(*(ob.matrix_world@me.vertices[i].co))for i in p.vertices):removed+=1
   else:faces.append(tuple(p.vertices))
  new=bpy.data.meshes.new(me.name+' pruned');new.from_pydata(vs,[],faces);new.update()
  for m in me.materials:new.materials.append(m)
  ob.data=new
 elif ob.name.startswith('Branch'):
  a=ob.matrix_world@Vector((0,0,min(v.co.z for v in ob.data.vertices)));b=ob.matrix_world@Vector((0,0,max(v.co.z for v in ob.data.vertices)))
  if any(occupied(*a.lerp(b,k/16))for k in range(17)):bpy.data.objects.remove(ob,do_unlink=True)
for ob in list(bpy.context.scene.objects):
 if ob.name.startswith('Validation sealed room'):bpy.data.objects.remove(ob,do_unlink=True)
for m in bpy.data.materials:
 if m.name.startswith('Glazing'):
  nt=m.node_tree;nt.links.new(nt.nodes.get('Principled BSDF').outputs[0],nt.nodes.get('Material Output').inputs['Surface'])
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'cleveland-daylight.blend'));bpy.ops.export_scene.gltf(filepath=str(P/'public/house.glb'),export_format='GLB',export_extras=True,export_cameras=False,export_lights=False)
print('PRUNED_LEAF_FACES',removed)
