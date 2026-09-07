import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import http from 'node:http';
const config=JSON.parse(await fs.readFile(new URL('../.runtime/host.json',import.meta.url),'utf8'));
const base='http://127.0.0.1:'+config.port,headers={Cookie:'daylight='+config.token};
assert.equal((await fetch(base+'/api/tailscale',{method:'POST'})).status,401);
assert.equal((await fetch(base+'/api/tailscale',{method:'POST',headers:{...headers,Origin:'https://untrusted.invalid','Content-Type':'application/json'},body:JSON.stringify({enabled:true})})).status,403);
const remoteStatus=await new Promise((resolve,reject)=>{const req=http.request(base+'/api/tailscale',{method:'POST',headers:{...headers,Host:'remote.example:5182','Content-Type':'application/json'}},res=>{res.resume();resolve(res.statusCode);});req.on('error',reject);req.end(JSON.stringify({enabled:true}));});assert.equal(remoteStatus,403);
assert.equal((await fetch(base+'/api/tailscale',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:'{}'})).status,400);
const connection=await (await fetch(base+'/api/connection',{headers})).json();assert.equal(connection.canConfigure,true);
if(connection.private){const site=new URL(connection.websiteUrl);assert.equal(site.hostname,'cleveland-sun-study.sammyhajalie2g.chatgpt.site');assert.equal(new URLSearchParams(site.hash.slice(1)).get('host'),connection.url);}
const html=await fs.readFile(new URL('../dist/index.html',import.meta.url),'utf8');
assert(!html.includes('<canvas'));assert(!html.includes('/app/main.js'));
let scriptBytes=0;for(const m of html.matchAll(new RegExp('(?:src|href)="(/assets/[^" ]+[.]js)"','g'))){const js=await fs.readFile(new URL('../dist'+m[1],import.meta.url),'utf8');scriptBytes+=Buffer.byteLength(js);assert(!/WebGLRenderer|WebGLPathTracer|house\.glb|render-.*\.js/.test(js));}
assert(scriptBytes<10000);assert((await fs.readFile(new URL('../dist/render.html',import.meta.url),'utf8')).includes('id="scene"'));
console.log(JSON.stringify({connectionAuthenticationPassed:true,remoteNetworkChangesRejected:true,websiteLinkRoundTripPassed:true,gatewayLoadsNoRenderer:true,gatewayScriptBytes:scriptBytes},null,2));
