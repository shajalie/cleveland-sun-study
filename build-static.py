from pathlib import Path
from html.parser import HTMLParser
import re
P=Path(__file__).parent
class Frame(HTMLParser):
 def handle_starttag(self,tag,attrs):
  if tag=='iframe':self.doc=dict(attrs)['srcdoc']
fragments=[]
for name,file,root in [('outdoor','outdoor-export.html','cleveland-sun-explorer'),('indoor','indoor-export.html','cleveland-indoor-sun')]:
 parser=Frame();parser.feed((P/file).read_text());doc=parser.doc
 frag=doc.split('<body>',1)[1].rsplit('</body>',1)[0]
 # The export's helper runtime is unnecessary: the models use native controls.
 source=(P/'src'/f'{name}.html').read_text()
 markup=source.split('<style>')[0];script=source.split('<script>')[1].split('</script>')[0]
 if name=='outdoor':
  script=script.replace('root.sunModel={sun,shade,',"root.sunModel={state:()=>({data,obstacles,trees,samples,days,current,lastSun}),sun,shade,")
  script=script.replace('updateDetails();draw();\n  }',"updateDetails();draw();document.dispatchEvent(new CustomEvent('sunmodelchange'));\n  }")
 else:
  script=script.replace('root.sunModel={sun,stats:',"root.sunModel={state:()=>({data,floor,samples,days,current,indoorShade}),sun,stats:")
  script=script.replace('detail();draw();}\n',"detail();draw();document.dispatchEvent(new CustomEvent('sunmodelchange'));}\n")
 # Data belongs to the model, with no network dependency.
 data=source[source.index('<script id='):source.index('<script>')]
 fragments.append('<section class="model-panel" id="panel-'+name+'" '+('hidden' if name=='indoor' else '')+'>'+markup+data+'</section><script>'+script+'</script>')
header='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="description" content="Explore approximate sunlight across the yards and rooms of 3014 Cleveland Avenue NW, including a first-person walk-through."><title>3014 Cleveland · Sun Study</title><link rel="stylesheet" href="/site.css"></head><body><header class="site-header"><div><span class="eyebrow">3014 CLEVELAND AVENUE NW</span><h1>Sun study</h1></div><span class="study-note">Exploratory model<br>Heights &amp; windows estimated</span></header><nav class="view-tabs" aria-label="Study view"><button data-panel="outdoor" aria-pressed="true">Outside</button><button data-panel="indoor" aria-pressed="false">Inside</button><button data-panel="walk" aria-pressed="false">Walk through</button></nav><main>'''
(P/'dist/index.html').write_text(header+'\n'.join(fragments)+'\n'+(P/'src/walk-panel.html').read_text()+'\n</main><script src="/walk.js"></script><script src="/site.js"></script></body></html>')
