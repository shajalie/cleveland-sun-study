import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomBytes,timingSafeEqual} from 'node:crypto';
import puppeteer from 'puppeteer-core';
import {WebSocketServer,WebSocket} from 'ws';
import QRCode from 'qrcode';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const runtime=path.join(root,'.runtime');await fs.mkdir(runtime,{recursive:true});
const port=Number(process.env.DAYLIGHT_PORT||5182),renderPort=Number(process.env.DAYLIGHT_RENDER_PORT||5181);
const stateFile=path.join(runtime,'host.json');let saved={};try{saved=JSON.parse(await fs.readFile(stateFile,'utf8'));}catch{}
const token=saved.token||randomBytes(24).toString('base64url');
let browser,page,gpu='',ready=false,failure='',lastStatus={},closing=false;
const clients=new Set(),keys=new Set();let lastInput=0,commandQueue=Promise.resolve(),statusBusy=false;const streamStats={frames:0,bytes:0,lastFrameAt:null};
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.svg':'image/svg+xml','.glb':'model/gltf-binary','.hdr':'application/octet-stream'};
const equal=(a,b)=>typeof a==='string'&&a.length===b.length&&timingSafeEqual(Buffer.from(a),Buffer.from(b));
const cookie=req=>(req.headers.cookie||'').split(';').map(x=>x.trim()).find(x=>x.startsWith('daylight='))?.slice(9);
const authorized=req=>equal(cookie(req),token);
const originOK=req=>!req.headers.origin||(()=>{try{return new URL(req.headers.origin).host===req.headers.host;}catch{return false;}})();
function json(res,code,value){res.writeHead(code,{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(JSON.stringify(value));}
async function body(req){let text='';for await(const chunk of req){text+=chunk;if(text.length>2048)throw Error('Request too large');}return JSON.parse(text||'{}');}
async function staticFile(res,base,relative){try{const file=path.resolve(base,relative);if(!file.startsWith(base+path.sep))return json(res,403,{error:'Forbidden'});const bytes=await fs.readFile(file);res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','X-Content-Type-Options':'nosniff','Cache-Control':'no-cache'});res.end(bytes);}catch{json(res,404,{error:'Not found'});}}
const sceneServer=http.createServer((req,res)=>{const u=new URL(req.url,'http://localhost');staticFile(res,path.join(root,'dist'),u.pathname==='/'?'index.html':decodeURIComponent(u.pathname).slice(1));});
await new Promise((resolve,reject)=>sceneServer.once('error',reject).listen(renderPort,'127.0.0.1',resolve));
const attempts=new Map();
const server=http.createServer(async(req,res)=>{try{
 const u=new URL(req.url,'http://localhost');res.setHeader('Referrer-Policy','no-referrer');res.setHeader('X-Frame-Options','DENY');
 if(u.pathname==='/health')return json(res,200,{service:'cleveland-daylight-host',pid:process.pid,ready});
 if(u.pathname==='/api/connect'&&req.method==='POST'){
  if(!originOK(req))return json(res,403,{error:'Origin denied'});
  const ip=req.socket.remoteAddress,attempt=attempts.get(ip)||{count:0,since:Date.now()};if(Date.now()-attempt.since>60000){attempt.count=0;attempt.since=Date.now();}if(attempt.count>=12)return json(res,429,{error:'Try again in a minute'});
  const b=await body(req);if(!equal(b.token,token)){attempt.count++;attempts.set(ip,attempt);return json(res,401,{error:'Incorrect pairing key'});}attempts.delete(ip);
  res.setHeader('Set-Cookie',`daylight=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000`);return json(res,200,{ok:true});
 }
 if(u.pathname==='/api/state')return authorized(req)?json(res,200,{ready,gpu,failure,stream:streamStats,...lastStatus}):json(res,401,{error:'Pair this browser'});
 if(u.pathname==='/api/connection'){
  if(!authorized(req))return json(res,401,{error:'Pair this browser'});let config={};try{config=JSON.parse((await fs.readFile(path.join(runtime,'connection.json'),'utf8')).replace(/^\uFEFF/,''));}catch{}
  const url=(config.phone_url||`http://127.0.0.1:${port}/`)+'#'+token;return json(res,200,{url,private:!!config.phone_url,qr:await QRCode.toDataURL(url,{width:300,margin:2})});
 }
 const files={'/':'client.html','/client.js':'client.js','/style.css':'style.css'};
 if(files[u.pathname])return staticFile(res,path.join(root,'remote'),files[u.pathname]);
 json(res,404,{error:'Not found'});
 }catch(e){json(res,400,{error:e.message});}});
const wss=new WebSocketServer({noServer:true,maxPayload:4096});
server.on('upgrade',(req,socket,head)=>{if(req.url!=='/control'||!authorized(req)||!originOK(req)){socket.end('HTTP/1.1 401 Unauthorized\r\nConnection: close\r\n\r\n');return;}wss.handleUpgrade(req,socket,head,ws=>wss.emit('connection',ws));});
function send(ws,obj){if(ws.readyState===WebSocket.OPEN)ws.send(JSON.stringify(obj));}
async function releaseKeys(){for(const k of keys)await page?.keyboard.up(k).catch(()=>{});keys.clear();}
const selectIds=new Set(['date','time','places','quality','exposure','canopy','glazing']);
const buttons=new Set(['appearance','direct','clear','overcast','main-floor','second-floor','walk','orbit','map-scope']);
async function action(a){
 if(!ready||!page)throw Error(failure||'GPU renderer is starting');
 if(a.type==='select'){
  if(!selectIds.has(a.id)||typeof a.value!=='string')throw Error('Invalid control');
  await page.evaluate(({id,value})=>{const e=document.getElementById(id);if(![...e.options].some(o=>o.value===value))throw Error('Invalid option');e.value=value;e.dispatchEvent(new Event('change',{bubbles:true}));if(id==='quality'&&value==='512'){window.study.pt.renderScale=.75;window.study.pt.reset();}},a);
 }else if(a.type==='button'){
  if(!buttons.has(a.id))throw Error('Invalid button');await page.evaluate(id=>document.getElementById(id).click(),a.id);
 }else if(a.type==='pointer'){
  if(!['down','up','move'].includes(a.phase)||!Number.isFinite(a.x)||!Number.isFinite(a.y))throw Error('Invalid pointer');
  const vp=page.viewport(),x=Math.max(0,Math.min(1,a.x))*vp.width,y=Math.max(0,Math.min(1,a.y))*vp.height;
  await page.mouse.move(x,y);if(a.phase==='down')await page.mouse.down();if(a.phase==='up')await page.mouse.up();lastInput=Date.now();
 }else if(a.type==='key'){
  if(!['w','a','s','d'].includes(a.key)||typeof a.down!=='boolean')throw Error('Invalid movement');
  if(a.down){keys.add(a.key);await page.keyboard.down(a.key);}else{keys.delete(a.key);await page.keyboard.up(a.key);}lastInput=Date.now();
 }else if(a.type==='step'){
  const direction={w:'forward',a:'left',s:'back',d:'right'}[a.key];if(!direction)throw Error('Invalid step');await page.evaluate(d=>document.querySelector('[data-move="'+d+'"]').click(),direction);
 }else if(a.type==='heartbeat'){lastInput=Date.now();
 }else if(a.type==='release'){await releaseKeys();await page.mouse.up();
 }else if(a.type==='map'){
  if(!Number.isFinite(a.x)||!Number.isFinite(a.y)||a.x<0||a.x>1||a.y<0||a.y>1)throw Error('Invalid map point');
  await page.evaluate(({x,y})=>{const e=document.getElementById('map'),r=e.getBoundingClientRect();e.dispatchEvent(new PointerEvent('pointerup',{clientX:r.left+x*r.width,clientY:r.top+y*r.height,bubbles:true}));},a);
 }else if(a.type==='zoom'){
  if(!Number.isFinite(a.delta))throw Error('Invalid zoom');await page.mouse.wheel({deltaY:Math.max(-300,Math.min(300,a.delta))});
 }else throw Error('Unknown action');
}
wss.on('connection',ws=>{clients.add(ws);send(ws,{type:'status',ready,gpu,failure,stream:streamStats,...lastStatus});ws.on('message',(raw,binary)=>{if(binary)return ws.close(1003);let a;try{a=JSON.parse(raw);}catch{return ws.close(1007);}
 commandQueue=commandQueue.then(()=>action(a)).catch(e=>send(ws,{type:'notice',message:e.message}));
 });ws.on('close',()=>{clients.delete(ws);releaseKeys();page?.mouse.up().catch(()=>{});});});
await new Promise((resolve,reject)=>server.once('error',reject).listen(port,process.env.DAYLIGHT_BIND||'127.0.0.1',resolve));
await fs.writeFile(stateFile,JSON.stringify({token,pid:process.pid,port,renderPort,started:new Date().toISOString()},null,2));
console.log(`HOST_LISTENING http://127.0.0.1:${port}/`);
async function startRenderer(){try{
 const candidates=[process.env.DAYLIGHT_BROWSER,'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','C:/Program Files/Microsoft/Edge/Application/msedge.exe','C:/Program Files/Google/Chrome/Application/chrome.exe'].filter(Boolean);
 let executablePath;for(const file of candidates){try{await fs.access(file);executablePath=file;break;}catch{}}if(!executablePath)throw Error('Install Microsoft Edge or set DAYLIGHT_BROWSER to your Chromium browser executable.');
 browser=await puppeteer.launch({executablePath,headless:true,pipe:true,userDataDir:path.join(runtime,'render-profile'),defaultViewport:{width:960,height:720,deviceScaleFactor:1},args:['--enable-gpu','--force-high-performance-gpu','--use-angle=d3d11','--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows'],timeout:60000});
 page=await browser.newPage();await page.goto(`http://127.0.0.1:${renderPort}/`,{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.study?.state.ready,{timeout:120000});
 gpu=await page.evaluate(()=>{const gl=window.study.renderer.getContext(),e=gl.getExtension('WEBGL_debug_renderer_info');return e?gl.getParameter(e.UNMASKED_RENDERER_WEBGL):'Unknown GPU';});
 if(!/NVIDIA.*(?:RTX|GeForce|Quadro)/i.test(gpu))throw Error(`Dedicated NVIDIA GPU was not selected: ${gpu}. Set the render browser to High performance in Windows Graphics settings and restart the launcher.`);
 await page.addStyleTag({content:'header,.view-top,.view-bottom,#pad,#reference-preview,#comparison,#toast{display:none!important}main{height:100vh!important}aside{position:fixed!important;display:block!important;left:-2000px!important;top:0!important;width:326px!important;height:900px!important}#workspace{width:100vw!important;height:100vh!important}'});
 await page.evaluate(()=>{window.study.pt.renderScale=.75;window.study.pt.reset();});
 ready=true;console.log('GPU_VERIFIED '+gpu);
 }catch(e){failure=e.message;console.error('HOST_ERROR '+failure);}}
startRenderer();
setInterval(async()=>{if(!page||!ready||statusBusy)return;statusBusy=true;if(keys.size&&Date.now()-lastInput>1500)await releaseKeys();try{
 lastStatus=await page.evaluate(()=>({state:window.study.state,toast:document.getElementById('toast').hidden?'':document.getElementById('toast').textContent,map:document.getElementById('map').outerHTML,mapTitle:document.getElementById('map-title').textContent,controls:Object.fromEntries(['date','time','places','quality','exposure','canopy','glazing'].map(id=>{const e=document.getElementById(id);return[id,{value:e.value,options:[...e.options].map(o=>({value:o.value,label:o.textContent}))}]})),pressed:Object.fromEntries(['appearance','direct','clear','overcast','main-floor','second-floor','walk','orbit'].map(id=>[id,document.getElementById(id).getAttribute('aria-pressed')==='true']))}));
 for(const ws of clients)send(ws,{type:'status',ready,gpu,failure,...lastStatus});
 }catch(e){failure=e.message;}finally{statusBusy=false;}},1000).unref();
async function frames(){while(!closing){const started=Date.now();if(ready&&clients.size){try{const frame=await page.screenshot({type:'jpeg',quality:82,encoding:'binary'});streamStats.frames++;streamStats.bytes=frame.length;streamStats.lastFrameAt=new Date().toISOString();for(const ws of clients)if(ws.readyState===WebSocket.OPEN&&ws.bufferedAmount<500000)ws.send(frame,{binary:true});}catch(e){failure=e.message;}}await new Promise(r=>setTimeout(r,Math.max(10,120-(Date.now()-started))));}}
frames();
async function close(){if(closing)return;closing=true;await releaseKeys();for(const ws of clients)ws.close();await browser?.close();server.close();sceneServer.close();process.exit(0);}
process.on('SIGINT',close);process.on('SIGTERM',close);
