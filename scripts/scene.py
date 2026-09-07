"""Blender 4.5: reproducible shared, meter-scale daylight scene."""
import bpy, math, json, sys, random
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1]
OUT=P/'public'; OUT.mkdir(exist_ok=True)
D=json.loads((P/'model-data.json').read_text()); I=D['indoor']; O=D['outdoor']; F=1200/3937
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def mat(name,color,rough=.7):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough
 return m
wall=mat('Plaster | reflectance 0.72',(.72,.70,.65)); ceiling=mat('Ceiling | reflectance 0.82',(.82,.82,.78)); wood=mat('Oak floor',(.25,.12,.055),.38);trim=mat('Dark wood trim',(.09,.04,.015),.4)
stone=mat('Limestone paving',(.38,.36,.31));grass=mat('Grass',(.075,.17,.035));roof=mat('Terracotta roof',(.22,.065,.027)); neighbor=mat('Neighbor masonry',(.35,.32,.28));leaf=mat('Tree canopy',(.055,.13,.025));trunk=mat('Bark',(.075,.045,.022));blue=mat('Pool water',(.025,.22,.24),.08);cloth=mat('Upholstery',(.32,.38,.30));rug=mat('Muted woven rug',(.16,.055,.045))
glass=mat('Glazing | neutral transmission 82%',(0,0,0),.1)
bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Alpha'].default_value=1;bs.inputs['Base Color'].default_value=(.943,.943,.943,1);bs.inputs['Transmission Weight'].default_value=1;bs.inputs['IOR'].default_value=1.5;bs.inputs['Roughness'].default_value=.012
glass.name='Glazing | dielectric glass'
blue.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=.96
blue.node_tree.nodes.get('Principled BSDF').inputs['IOR'].default_value=1.333
blue.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.80,.95,.96,1)
blue.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.035
leaf.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=.12
leaf.node_tree.nodes.get('Principled BSDF').inputs['IOR'].default_value=1.35
metal=mat('Black iron',(.035,.033,.029),.35);metal.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.7
linen=mat('Ivory linen',(.67,.64,.56),.85);leather=mat('Cognac leather',(.28,.115,.04),.38)
def texture(m,name,scale):
 n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OUT/'textures'/(name+'.png')),check_existing=True);l.new(tex.outputs['Color'],bs.inputs['Base Color']);normal=n.new('ShaderNodeTexImage');normal.image=bpy.data.images.load(str(OUT/'textures'/(name+'-normal.png')),check_existing=True);normal.image.colorspace_settings.name='Non-Color';nm=n.new('ShaderNodeNormalMap');l.new(normal.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal']);m['tex_scale']=scale
for m,n,sc in [(wood,'oak',4),(wall,'plaster',.8),(stone,'stone',2),(grass,'grass',2),(rug,'weave',1),(roof,'tile',3)]:texture(m,n,sc)
objects=[]; collision=[]
def finish(obj,name,material,walk=False,solid=False):
 obj.name=name;obj.data.materials.append(material);obj['walkable']=walk;obj['solid']=solid;objects.append(obj)
 if solid: collision.append({'name':name,'min':[min((obj.matrix_world@Vector(c))[k] for c in obj.bound_box) for k in range(3)],'max':[max((obj.matrix_world@Vector(c))[k] for c in obj.bound_box) for k in range(3)]})
 return obj
def box(name,x,y,z,sx,sy,sz,m,solid=False):
 if min(sx,sy,sz)<.0001:return
 bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,z));o=bpy.context.object;o.dimensions=(sx,sy,sz);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,name,m,False,solid)
def slab(name,poly,z,depth,m,walk=False):
 poly=[tuple(p) for p in poly];poly=poly[:-1] if poly[0]==poly[-1] else poly
 n=len(poly);vs=[(x,y,h) for h in [z-depth,z] for x,y in poly];faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
 bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT');o.select_set(False)
 return finish(o,name,m,walk)
def band(name,a,b,lo,hi,width,m,solid=False):
 dx=b[0]-a[0];dy=b[1]-a[1];o=box(name,(a[0]+b[0])/2,(a[1]+b[1])/2,(lo+hi)/2,math.hypot(dx,dy),width,hi-lo,m)
 if o:o.rotation_euler.z=math.atan2(dy,dx)
 return o

def shaped_band(name,a,b,al,bl,ah,bh,width,m):
 dx=b[0]-a[0];dy=b[1]-a[1];L=math.hypot(dx,dy)
 if L<.0001:return
 nx=-dy/L*width/2;ny=dx/L*width/2
 vs=[(p[0]+q*nx,p[1]+q*ny,z)for q in [-1,1]for p,z in [(a,al),(b,bl),(b,bh),(a,ah)]]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],[(0,1,2,3),(7,6,5,4),(0,4,5,1),(3,2,6,7),(0,3,7,4),(1,5,6,2)]);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);finish(o,name,m)
for fidx,f in enumerate(I['floors']):
 base=f['base'];top=base+f['ceiling'];slab('Floor '+str(fidx),f['outline'],base,.20,wood,True);slab('Ceiling '+str(fidx),f['outline'],top+.20,.20,ceiling)
 for wi,w in enumerate(f['walls']):
  a=w['a'];b=w['b'];dx=b[0]-a[0];dy=b[1]-a[1];L=math.hypot(dx,dy);pt=lambda t:(a[0]+dx*t/L,a[1]+dy*t/L)
  hs=[];cuts=[0,L]
  for h in w['holes']:
   ts=sorted([((p[0]-a[0])*dx+(p[1]-a[1])*dy)/L for p in [h['a'],h['b']]])
   h={**h,'start':max(0,ts[0]),'end':min(L,ts[1])};hs.append(h);cuts+=ts
   if h.get('arch'):cuts += [ts[0]+(ts[1]-ts[0])*j/32 for j in range(1,32)]
  cuts=sorted(set(max(0,min(L,t)) for t in cuts))
  for l,r in zip(cuts,cuts[1:]):
   if r-l<.001:continue
   h=next((h for h in hs if h['start']<=(l+r)/2<=h['end']),None);name=f'Wall {fidx}.{wi}'
   if not h:band(name,pt(l),pt(r),base,top,.20 if w['ext'] else .14,wall);continue
   sill=h.get('sill',0 if not h['window'] or h.get('floorGlass') else .8);head=h.get('head',2.4 if h['window'] else 2.15)
   hl=hr=head
   if h.get('arch'):
    rise=min(.5,(h['end']-h['start'])/2)
    def archHead(t):
     u=(t-h['start'])/(h['end']-h['start']);return head-rise*(1-math.sqrt(max(0,1-(2*u-1)**2)))
    hl=archHead(l);hr=archHead(r)
   if sill>0:band(name,pt(l),pt(r),base,base+sill,.20,wall)
   shaped_band(name,pt(l),pt(r),base+hl,base+hr,top,top,.20,wall)
   if h['window']:shaped_band('Glass',pt(l),pt(r),base+sill,base+sill,base+hl,base+hr,.005,glass)
  for h in hs:
   sill=h.get('sill',0 if not h['window'] or h.get('floorGlass') else .8);head=h.get('head',2.4 if h['window'] else 2.15)
   if h['window']:
    for t in [h['start'],h['end']]:band('Window jamb',pt(t-.03),pt(t+.03),base+sill,base+head,.25,trim)
    band('Window sill',pt(h['start']),pt(h['end']),base+sill,base+sill+.045,.27,trim)
    if not h.get('arch'):
     band('Window head',pt(h['start']),pt(h['end']),base+head-.04,base+head,.24,trim)
     for j in range(1,max(2,round((h['end']-h['start'])/.7))):
      t=h['start']+(h['end']-h['start'])*j/max(2,round((h['end']-h['start'])/.7));band('Mullion',pt(t-.012),pt(t+.012),base+sill,base+head,.08,trim)
     band('Window rail',pt(h['start']),pt(h['end']),base+(sill+head)/2,base+(sill+head)/2+.025,.08,trim)
 # Foundation and inter-floor spandrels close the full exterior envelope.
 for w in f['walls']:
  if w['ext']:band('Foundation' if fidx==0 else 'Spandrel',w['a'],w['b'],0 if fidx==0 else 3.7,base,.22,stone if fidx==0 else wall)
 # restrained furniture communicates scale without inventing the listing contents
 for r in f['rooms']:
  x,y=r['label'];nm=r['name']
  if nm in ['Living','Dining','Study'] or 'bedroom' in nm.lower():
   box('Rug',x,y,base+.012,2.6,2.5,.02,rug)
  if nm=='Dining':
   box('Dining table',x,y,base+.76,1.8,1.05,.08,wood,True)
   for xx in [-.75,.75]:
    for yy in [-.38,.38]:box('Table leg',x+xx,y+yy,base+.37,.06,.06,.74,trim)
  if nm=='Living':
   box('Sofa',15.8,18,base+.4,.85,2.4,.8,cloth,True);box('Sofa back',16.12,18,base+.8,.22,2.4,.7,cloth)
  if nm=='Study':
   box('Study ottoman',15.4,24.8,base+.25,1.0,.8,.5,cloth,True)
   for yy in [22.6,23.4,24.2,25.0,25.8]:box('Study ceiling beam',14.75,yy,top-.10,4.5,.12,.20,trim)
  if 'bedroom' in nm.lower():box('Bed',x-1,y+1,base+.32,1.8,2.05,.64,cloth,True)
  if nm=='Sunroom':box('Sunroom desk',5.7,25.8,base+.74,1.65,.62,.08,wood,True)
 # continuous narrow floorboards, slight reflectance variation, no fake illumination
 for w in f['walls']:
  if w['ext']:continue
  # lower skirting follows intact wall segments only; wall geometry carries shading
slab('Context ground',[[-2000,-2000],[2000,-2000],[2000,2000],[-2000,2000]],-.10,.15,grass)
parcel=[[x*F,y*F]for x,y in O['parcel']];slab('Property ground',parcel,0,.1,grass,True)
for i,z in enumerate(O['zones'][1:]):
 poly=[[x*F,y*F]for x,y in z['poly']];m=grass if 'lawn' in z['name'].lower() else stone
 slab(z['name'],poly,.8 if 'Upper' in z['name'] else .4 if 'Lower' in z['name'] else .016,.8 if 'Upper' in z['name'] else .4 if 'Lower' in z['name'] else .015,roof if 'terrace' in z['name'] else m,True)
pool=[[x*F,y*F]for x,y in O['zones'][0]['poly']];slab('Pool water | no access',pool,.04,.69,blue)
slab('Pool basin',pool,-.65,.1,mat('Pool tile',(.22,.52,.55),.3))
cut=slab('Pool excavation cutter',pool,.12,2,stone)
for ob in objects[:]:
 if ob.name not in ['Property ground','Context ground','Pool deck / surround']:continue
 mod=ob.modifiers.new('Pool excavation','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
objects.remove(cut);bpy.data.objects.remove(cut,do_unlink=True)

for f in I['floors'][1:]:slab('Roof deck',f['outline'],7.18,.25,roof)
# Shallow hipped main roof, corrected to the indoor footprint.
rp=[[4.1,13.4],[17.4,13.4],[17.4,22.35],[4.1,22.35]];ri=[[7,16],[14.5,16],[14.5,19.75],[7,19.75]]
mesh=bpy.data.meshes.new('Hip roof');mesh.from_pydata([(x,y,7.02)for x,y in rp]+[(x,y,8.25)for x,y in ri],[],[(i,(i+1)%4,(i+1)%4+4,i+4)for i in range(4)]+[(4,5,6,7)]);mesh.update();ob=bpy.data.objects.new('Hip roof',mesh);bpy.context.collection.objects.link(ob);finish(ob,'Hip roof',roof)
for b in O['buildings']:
 if b['kind']=='porch':
  poly=[[x*F,y*F]for x,y in b['poly']];slab(b['name']+' roof',poly,b['height'],.18,ceiling);slab(b['name']+' paving',poly,.10,.1,stone,True)
  for x,y in poly:box('Porch column',x,y,1.6,.20,.20,3.2,wall,True)
for b in O['neighbors']:
 poly=[[x*F,y*F]for x,y in b['ring']];slab('Neighbor '+str(b['id']),poly,9,9,neighbor)
# Photo-informed joinery and furnishings. Geometry remains explicitly approximate.
def rounded(name,x,y,z,sx,sy,sz,m,bevel=.045,solid=False):
 o=box(name,x,y,z,sx,sy,sz,m,solid)
 mod=o.modifiers.new('Soft manufactured edges','BEVEL');mod.width=bevel;mod.segments=3
 bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
 for p in o.data.polygons:p.use_smooth=True
 return o
def rod(name,a,b,r,m):
 a=Vector(a);b=Vector(b);d=b-a;bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=r,depth=d.length,location=(a+b)/2);o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return finish(o,name,m)
def chair(x,y,z,angle=0):
 rounded('Chair upholstered seat',x,y,z+.47,.46,.46,.11,linen,.035)
 rounded('Chair back',x,y+.20,z+.79,.46,.09,.55,wood,.025)
 for dx in [-.18,.18]:
  for dy in [-.18,.18]:rod('Chair leg',(x+dx,y+dy,z),(x+dx,y+dy,z+.45),.018,trim)
for f in I['floors']:
 b=f['base'];top=b+f['ceiling']
 for w in f['walls']:
  a=w['a'];bb=w['b'];dx=bb[0]-a[0];dy=bb[1]-a[1];L=math.hypot(dx,dy)
  # Cornice above doors and glazing, continuous around the enclosed rooms.
  band('Crown moulding',a,bb,top-.07,top-.015,.25,ceiling)
  if not w['holes']:band('Painted skirting',a,bb,b,b+.14,.235,ceiling)
for yy in [14.5,15.7,16.9,18.1,19.3,20.5]:box('Living ceiling beam',14.7,yy,3.60,4.5,.14,.2,trim)
# Living sofa cushions, armchairs and fireplace seen in the listing.
for yy in [17.25,18.0,18.75]:rounded('Leather seat cushion',15.63,yy,1.29,.68,.7,.20,leather,.08)
for yy in [16.85,19.15]:rounded('Sofa arm',15.78,yy,1.38,.82,.18,.43,leather,.07)
rounded('Low coffee table',14.15,18.05,1.17,.7,1.4,.1,wood,.04,True)
for x,y in [(13.25,15.4),(13.25,16.4)]:chair(x,y,.8)
box('Fireplace hearth',16.9,15.5,.90,.45,1.45,.2,stone)
box('Fireplace black recess',16.94,15.5,1.48,.03,.83,.8,metal)
box('Fireplace mantel',16.70,15.5,2.03,.56,1.4,.13,ceiling)
for yy in [14.9,16.1]:box('Fireplace surround',16.79,yy,1.47,.3,.15,1.1,ceiling)
for yy in [15.45,16.05,16.65]:
 for xx in [5.6,8.0]:chair(xx,yy,.8)
# Kitchen cabinetry fitted along side walls, stone worktops and individual doors.
for xx in [4.8,7.47]:
 for yy in [22.65,23.30,23.95,24.60,25.25]:
  rounded('Kitchen base cabinet',xx,yy,1.22,.58,.61,.84,ceiling,.008,True)
  box('Stone worktop',xx,yy,1.68,.65,.65,.045,stone)
  rod('Cabinet handle',(xx+(.30 if xx<6 else -.30),yy-.12,1.44),(xx+(.30 if xx<6 else -.30),yy+.12,1.44),.009,metal)
# Study built-ins, wainscot panels and softened sofa.
for yy in [22.7,23.5,24.3,25.1]:
 box('Study panel',16.94,yy,1.22,.04,.73,.8,ceiling)
for zz in [1.15,1.65,2.15,2.65]:box('Study bookshelf',12.65,25.05,zz,.34,1.5,.045,wood)
for yy in [24.30,25.8]:box('Bookcase upright',12.65,yy,1.88,.36,.06,2.1,ceiling)
for j in range(17):box('Book',12.64,24.4+j*.075,1.88,.23,.054,.30,mat('Book '+str(j),(.08+.01*(j%5),.11+.015*(j%3),.07+.02*(j%4))))
rounded('Study sofa',16.22,24.1,1.19,.80,1.65,.60,cloth,.10,True)
rounded('Study sofa back',16.52,24.1,1.52,.22,1.68,.76,cloth,.06)
for yy in [23.62,24.35]:rounded('Study cushion',16.1,yy,1.53,.59,.64,.15,cloth,.06)
# Sunroom joinery and bedroom bedding.
for xx in [4.60,6.83]:box('Sunroom low cabinet',xx,24.2,4.18,.35,3.8,.46,ceiling)
for yy in [23.4,24.2,25.0]:box('Sunroom desk support',5.7,25.8,4.31,.06,.06,.73,trim)
chair(5.65,25.08,3.95)
for room in I['floors'][1]['rooms']:
 if 'bedroom' not in room['name'].lower():continue
 x,y=room['label'];x-=1;y+=1
 rounded('Duvet',x,y,4.64,1.79,2.04,.22,linen,.12)
 rounded('Headboard',x,y+1.0,4.73,1.86,.13,1.1,cloth,.035)
 for xx in [x-.46,x+.46]:rounded('Pillow',xx,y+.65,4.84,.66,.44,.17,linen,.08)
# Rear terrace railing, steps and table, inferred from the exterior photos.
for x in [11.0,11.55,12.1,12.65,13.2,13.75,14.3,14.85,15.4]:
 rod('Terrace baluster',(x,30.15,.80),(x,30.15,1.7),.013,metal)
rod('Terrace handrail',(11,30.15,1.7),(15.4,30.15,1.7),.027,metal)
for j in range(4):box('Terrace step',12.1,30.45+j*.30,.70-j*.2,1.6,.31,.2,roof)
rounded('Outdoor table',14.15,28.15,1.55,1.3,1.3,.08,wood,.35,True)
for xx,yy in [(13.25,28.15),(15.05,28.15),(14.15,27.25),(14.15,29.05)]:chair(xx,yy,.8)
# Real leaf geometry replaces solid crown blobs. Deterministic estimated density.
def occupied(x,y,z):
 def inside(p,poly):
  hit=False
  for i,a in enumerate(poly):
   b=poly[i-1]
   if (a[1]>p[1])!=(b[1]>p[1]) and p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:hit=not hit
  return hit
 if z<8.5 and 3.9<x<17.6 and 13.2<y<22.55:return True
 return z<7.4 and any(inside((x+dx,y+dy),f['outline'])for f in I['floors']for dx,dy in [(0,0),(.2,0),(-.2,0),(0,.2),(0,-.2)])
random.seed(3014)
for ti,t in enumerate(O['trees']):
 x,y,r,top=t;x*=F;y*=F;r*=F;rz=min(top*.42,r*1.5);zc=top-rz
 rod('Trunk',(x,y,0),(x,y,zc),.15,trunk)
 box('Trunk collision',x,y,zc/2,.20,.20,zc,trunk,True)
 vs=[];faces=[]
 for j in range(2600):
  az=random.random()*math.tau;zz=random.uniform(-1,1);rr=math.sqrt(1-zz*zz)*r*random.random()**.4
  c=Vector((x+rr*math.cos(az),y+rr*math.sin(az),zc+zz*rz));a=random.random()*math.tau
  u=Vector((math.cos(a),math.sin(a),random.uniform(-.5,.5)))*random.uniform(.075,.14);v=Vector((-math.sin(a)*.45,math.cos(a)*.45,random.uniform(-.4,.4)))*random.uniform(.10,.17)
  if any(occupied(p.x,p.y,p.z)for p in [c-u,c+v,c+u,c-v]):continue
  k=len(vs);vs.extend([c-u,c+v,c+u,c-v]);faces.append((k,k+1,k+2,k+3))
 mesh=bpy.data.meshes.new('Individual leaves');mesh.from_pydata(vs,[],faces);mesh.update();ob=bpy.data.objects.new('Leaves '+str(ti),mesh);bpy.context.collection.objects.link(ob);finish(ob,'Leaves '+str(ti),leaf);ob['tree']=True;ob['tree_center']=[x,y,zc]
 for j in range(12):
  a=j*2.399;end=(x+r*.7*math.cos(a),y+r*.7*math.sin(a),zc+rz*(j/12-.4))
  if any(occupied(x+(end[0]-x)*q,y+(end[1]-y)*q,zc-rz*.65+(end[2]-zc+rz*.65)*q)for q in [k/16 for k in range(17)]):continue
  rod('Branch',(x,y,zc-rz*.65),end,.025,trunk)
# Explicit planar UVs in world meters are exported, so both engines see the same maps.
bpy.context.view_layer.update()
for ob in objects:
 if ob.type!='MESH' or not ob.data.materials:continue
 m=ob.data.materials[0]
 if 'tex_scale' not in m:continue
 uv=ob.data.uv_layers.new(name='UVMap') if not ob.data.uv_layers else ob.data.uv_layers.active
 for poly in ob.data.polygons:
  normal=ob.matrix_world.to_3x3()@poly.normal;axis=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3)if i!=axis]
  for li in poly.loop_indices:
   p=ob.matrix_world@ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/m['tex_scale'],p[axes[1]]/m['tex_scale'])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=128;scene.cycles.max_bounces=20;scene.cycles.diffuse_bounces=12;scene.cycles.transmission_bounces=16;scene.cycles.transparent_max_bounces=24;scene.cycles.use_denoising=True
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for dev in prefs.devices:dev.use=dev.type=='OPTIX'
 scene.cycles.device='GPU';print('CYCLES_DEVICES',[(d.name,d.type,d.use)for d in prefs.devices])
except Exception as e:print('CPU fallback',e);scene.cycles.device='CPU'
scene.render.resolution_x=960;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
bpy.ops.object.camera_add(location=(14.55,19.5,2.42));cam=bpy.context.object;cam.name='Reference camera';cam.data.lens=21.6;cam.data.sensor_width=36;scene.camera=cam
cam.rotation_euler=(Vector((14.8,25,1.9))-cam.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Daylight sky');world.use_nodes=True;scene.world=world
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'cleveland-daylight.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'house.glb'),export_format='GLB',export_extras=True,export_cameras=False,export_lights=False)
(OUT/'model.json').write_text(json.dumps(D));(OUT/'collision.json').write_text(json.dumps(collision))
print('SCENE_READY',len(objects))
