import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(P/'cleveland-bake.blend'))
out=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.get('lightmap_group'):continue
 uv=o.data.uv_layers['Lightmap'];xs=[v.uv.x for v in uv.data];ys=[v.uv.y for v in uv.data]
 out.append({'name':o.name,'group':o['lightmap_group'],'uv':[min(xs),min(ys),max(xs),max(ys)]})
(P/'.runtime/uv-audit.json').write_text(json.dumps(out))
print(out[:8]);print('OBJECTS',len(out))
