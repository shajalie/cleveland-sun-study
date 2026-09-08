import bpy,numpy as np,json
from pathlib import Path
P=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(P/'cleveland-bake.blend'));s=bpy.context.scene
o=bpy.data.objects['Wall 0.001'];bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
m=bpy.data.materials.new('UV verification');m.use_nodes=True;n=m.node_tree.nodes;n.clear();em=n.new('ShaderNodeEmission');out=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(em.outputs[0],out.inputs['Surface']);target=bpy.data.images.new('White UV test',width=512,height=512,float_buffer=True);tex=n.new('ShaderNodeTexImage');tex.image=target;n.active=tex;o.data.materials.clear();o.data.materials.append(m)
for p in o.data.polygons:p.material_index=0
s.render.engine='CYCLES';s.cycles.samples=1;s.render.bake.margin=0;s.render.bake.use_clear=True
bpy.ops.object.bake(type='EMIT',uv_layer='Lightmap')
actual=np.asarray(target.pixels[:]).reshape(512,512,4)[:,:,0]>.5;expected=np.zeros((512,512),bool);o.data.calc_loop_triangles();uv=o.data.uv_layers['Lightmap']
for t in o.data.loop_triangles:
 a,b,c=[np.array(uv.data[li].uv)*512 for li in t.loops];lo=np.maximum(0,np.floor(np.minimum(np.minimum(a,b),c)).astype(int));hi=np.minimum(512,np.ceil(np.maximum(np.maximum(a,b),c)).astype(int));yy,xx=np.mgrid[lo[1]:hi[1],lo[0]:hi[0]];p=np.stack([xx+.5,yy+.5],axis=-1);cross=lambda u,v:u[...,0]*v[...,1]-u[...,1]*v[...,0];den=cross(b-a,c-a)
 if abs(den)<1e-8:continue
 v=cross(p-a,c-a)/den;w=cross(b-a,p-a)/den;expected[lo[1]:hi[1],lo[0]:hi[0]]|=(v>=0)&(w>=0)&(v+w<=1)
print('UV_MASK',json.dumps({'actual':int(actual.sum()),'expected':int(expected.sum()),'iou':float((actual&expected).sum()/max(1,(actual|expected).sum())),'flipped_iou':float((actual[::-1]&expected).sum()/max(1,(actual[::-1]|expected).sum()))}))
