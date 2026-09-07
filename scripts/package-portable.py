"""Build a self-contained Windows host ZIP from committed source and verified dist.

Includes Node runtime and installed JS dependencies, but no browser profiles,
pairing keys, credentials, .git data, or personal tailnet state.
"""
from pathlib import Path
import subprocess, zipfile, json, hashlib, shutil, sys
P=Path(__file__).resolve().parents[1]
output=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else P.parent.parent/'cleveland-daylight-windows.zip'
node=Path(shutil.which('node') or '')
assert node.is_file(),'Node executable is required for the Windows portable package'
assert (P/'dist/index.html').is_file(),'Build the website first'
assert (P/'cleveland-daylight.blend').is_file(),'Packed scene is missing'
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=P).decode().split('\0')
entries={name:P/name for name in tracked if name and (P/name).is_file()}
for directory in ['dist','node_modules']:
 for f in (P/directory).rglob('*'):
  if f.is_file() and not f.is_symlink(): entries[f.relative_to(P).as_posix()]=f
entries['final-render.log']=P/'final-render.log'
entries['runtime/node.exe']=node
entries['runtime/LICENSE']=P/'remote/NODE-LICENSE.txt'
for name in ['LICENSE','LICENSE.txt']:
 if (node.parent/name).is_file():entries['runtime/'+name]=node.parent/name
assert not any('.runtime/' in n or '/.git/' in n or n.startswith('.env') for n in entries)
with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name,file in sorted(entries.items()):z.write(file,'cleveland-daylight/'+name)
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 names=set(z.namelist())
 for name in ['START-DAYLIGHT.cmd','remote/server.mjs','runtime/node.exe','node_modules/puppeteer-core/package.json','dist/index.html','cleveland-daylight.blend','remote-validation.json']:
  assert 'cleveland-daylight/'+name in names,name+' missing'
 assert not any('/.runtime/' in name for name in names)
report={'file':output.name,'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'sourceCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=P).decode().strip(),'files':len(names),'includesCredentials':False,'nodeVersion':subprocess.check_output([str(node),'--version']).decode().strip()}
output.with_suffix('.manifest.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
