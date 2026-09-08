import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(P/'cleveland-bake.blend'))
report=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.get('lightmap_group'):continue
 if not o.name.startswith(('Wall','Arch','Floor','Ceiling','Privacy')):continue
 report.append({'name':o.name,'mesh':o.data.name,'users':o.data.users,'group':o['lightmap_group'],'uvs':[{ 'name':uv.name,'min':[min(v.uv[k] for v in uv.data) for k in [0,1]],'max':[max(v.uv[k] for v in uv.data) for k in [0,1]],'first':[list(v.uv) for v in list(uv.data)[:4]]} for uv in o.data.uv_layers]})
(P/'.runtime/atlas-audit.json').write_text(json.dumps(report,indent=2));print('SHARED',[(r['name'],r['users']) for r in report if r['users']>1]);print(json.dumps(report[:4]))
