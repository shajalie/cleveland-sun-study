"""Independent solar check plus paired image checks (pixel values are not lux)."""
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pvlib
from PIL import Image
P=Path(__file__).resolve().parents[1]
rows=[]
for s in json.loads((P/'public/scenarios.json').read_text()):
 expected=pvlib.solarposition.get_solarposition(pd.DatetimeIndex([s['sun']['instant']]),38.92485352,-77.06033745,altitude=90)
 rows.append({'date':s['date'],'local_time':s['sun']['clock'],'elevation_error_degrees':abs(float(expected.elevation.iloc[0])-s['sun']['alt']),'azimuth_error_degrees':abs(float(expected.azimuth.iloc[0])-s['sun']['az'])})
assert max(r['elevation_error_degrees'] for r in rows)<.3
assert max(r['azimuth_error_degrees'] for r in rows)<.3
def im(name):return np.asarray(Image.open(P/'public/references'/(name+'.png')).convert('RGB'),dtype=float)/255
sealed=im('sealed-room');assert sealed.max()<=1/255,'Sealed-room light leak'
# Same interior wall region, same camera and exposure. This is a relative image check.
def wall_mean(name):return float(im(name)[200:500,265:335].mean())
full=wall_mean('study-overcast');no_bounce=wall_mean('study-overcast-no-bounce');dark_glass=wall_mean('study-overcast-dark-glass');dark_walls=wall_mean('study-overcast-dark-walls')
assert full>no_bounce*1.15,'Indirect contribution missing'
assert full>dark_glass,'Reduced transmission should darken this wall'
assert full>dark_walls,'Reduced reflectance should darken this wall'
report={'solar_engine_reference':'pvlib 0.15.2, NREL SPA, geometric elevation','solar':rows,'sealed_room_max_display_pixel':float(sealed.max()),'fixed_exposure_wall_display_means':{'full':full,'no_diffuse_bounce':no_bounce,'55_percent_glazing':dark_glass,'30_percent_wall_reflectance':dark_walls},'note':'Display pixel values validate qualitative trends only. They are not luminance or lux.'}
report['generated_at_utc']=datetime.now(timezone.utc).isoformat()
report['input_sha256']={name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in ['public/house.glb','public/model.json','public/skies/manifest.json','scripts/render.py']}
report['reference_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((P/'public/references').glob('*.png'))}
(P/'validation-results.json').write_text(json.dumps(report,indent=2));(P/'public/validation-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
