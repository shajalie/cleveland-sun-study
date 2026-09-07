import requests,re,json,html
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageOps,ImageDraw
P=Path(__file__).resolve().parents[1]/'evidence';P.mkdir(exist_ok=True)
s=requests.get('https://www.compass.com/homedetails/3014-Cleveland-Ave-NW-Washington-DC-20008/1UXTV4_pid/').text
(P/'compass.html').write_text(s,encoding='utf8')
urls=list(dict.fromkeys(re.findall(r'https://www.compass.com/m/[^\s"<>]+?/(?:origin|[0-9x]+)/?\.(?:webp|jpg)',html.unescape(s))))
if not urls:
 urls=list(dict.fromkeys(re.findall(r'https://www.compass.com/m/[^\s"<>]+?\.(?:webp|jpg)',html.unescape(s))))
# First 56 include the subject's photos, duplicated hero sizes and floor plan.
# Later page images are unrelated recommended listings.
urls=urls[:56]
(P/'image-urls.json').write_text(json.dumps(urls,indent=2));print('Source images',len(urls))
def get(it):
 i,url=it
 if (P/f'{i:02d}.webp').exists():return
 r=requests.get(url);r.raise_for_status();(P/f'{i:02d}.webp').write_bytes(r.content)
with ThreadPoolExecutor(max_workers=6)as pool:list(pool.map(get,enumerate(urls)))
for start in range(0,len(urls),12):
 im=Image.new('RGB',(1200,900),'#eeeeee');dr=ImageDraw.Draw(im)
 for i in range(start,min(start+12,len(urls))):
  x=((i-start)%3)*400;y=((i-start)//3)*225;pic=ImageOps.contain(Image.open(P/f'{i:02d}.webp'),(400,200));im.paste(pic,(x,y));dr.text((x+4,y+202),str(i),fill='black')
 im.save(P/f'contact-{start}.jpg')
