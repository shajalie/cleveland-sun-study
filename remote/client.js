const $=id=>document.getElementById(id);let socket,currentURL,held=new Set(),dragging=false,lastMove=0,lastStatus,everFrame=false;
function enableControls(enabled){for(const e of document.querySelectorAll('#app button,#app select'))e.disabled=!enabled;}
const send=a=>{if(socket?.readyState===1)socket.send(JSON.stringify(a));};
function notice(message){$('notice').textContent=message;}
async function pair(token){const r=await fetch('/api/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});if(!r.ok)throw Error((await r.json()).error);history.replaceState(null,'',location.pathname);connect();}
$('pair-form').onsubmit=e=>{e.preventDefault();pair($('pair-key').value.trim()).catch(e=>$('pair-error').textContent=e.message);};
function update(s){lastStatus=s;enableControls(!!s.ready&&socket?.readyState===1);$('gpu').textContent=s.gpu?'Host GPU · '+(s.gpu.match(/NVIDIA, (.*?)(?: \(0x| Direct3D)/)?.[1]||s.gpu):'Checking host GPU…';if(s.failure){notice(s.failure);$('waiting').textContent=s.failure;return;}if(!s.ready){$('waiting').textContent='Starting the GPU renderer…';return;}
 if(s.toast)notice(s.toast);if(s.state){$('location').textContent=s.state.level?'Second floor':'House & garden';$('samples').textContent=`${Math.floor(s.state.samples)} samples · ${s.state.mode==='appearance'?20:1} bounces · ${s.state.sky}`;}
 if(s.ready&&!everFrame)$('waiting').textContent='Preparing the first live view…';if(s.controls)for(const [id,c] of Object.entries(s.controls)){const e=$(id);if(!e.options.length||e.options.length!==c.options.length){e.replaceChildren(...c.options.map(o=>new Option(id==='quality'?(o.value==='512'?'Responsive · 512 samples':'Fine · 2048 samples'):o.label,o.value)));}if(document.activeElement!==e)e.value=c.value;}
 if(s.controls?.places){const c=s.controls.places;$('location').textContent=c.options.find(o=>o.value===c.value)?.label||'Explore';}
 if(s.map){$('map-wrap').innerHTML=s.map;$('map-title').textContent=s.mapTitle;}
 for(const b of document.querySelectorAll('[data-button]'))if(b.dataset.button in (s.pressed||{}))b.setAttribute('aria-pressed',s.pressed[b.dataset.button]);
}
function connect(){enableControls(false);$('pair').hidden=true;$('app').hidden=false;socket=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/control');socket.onmessage=e=>{if(typeof e.data==='string'){const s=JSON.parse(e.data);if(s.type==='notice')notice(s.message);else update(s);return;}const url=URL.createObjectURL(e.data),old=currentURL;currentURL=url;$('stream').onload=()=>{if(old)URL.revokeObjectURL(old);$('waiting').hidden=true;everFrame=true;};$('stream').src=url;};socket.onopen=()=>{enableControls(!!lastStatus?.ready);notice('Connected to the desktop renderer');};socket.onclose=()=>{enableControls(false);held.clear();notice('Connection lost. Reconnecting…');setTimeout(check,2000);};}
async function check(){try{const r=await fetch('/api/state');if(r.ok){update(await r.json());connect();}else{$('pair').hidden=false;$('app').hidden=true;}}catch{notice('The render computer is unreachable. Keep it and Tailscale running.');setTimeout(check,3000);}}
for(const id of ['date','time','places','quality','exposure','canopy','glazing'])$(id).onchange=()=>send({type:'select',id,value:$(id).value});
for(const b of document.querySelectorAll('[data-button]'))b.onclick=()=>send({type:'button',id:b.dataset.button});
for(const b of document.querySelectorAll('[data-zoom]'))b.onclick=()=>send({type:'zoom',delta:+b.dataset.zoom});
function point(e){const r=$('stream').getBoundingClientRect(),w=Math.min(r.width,r.height*4/3),h=w*3/4;return {x:(e.clientX-r.left-(r.width-w)/2)/w,y:(e.clientY-r.top-(r.height-h)/2)/h};}
$('stream').onpointerdown=e=>{e.preventDefault();dragging=true;e.target.setPointerCapture(e.pointerId);send({type:'pointer',phase:'down',...point(e)});};
$('stream').onpointermove=e=>{if(!dragging||performance.now()-lastMove<33)return;lastMove=performance.now();send({type:'pointer',phase:'move',...point(e)});};
$('stream').onpointerup=e=>{dragging=false;send({type:'pointer',phase:'up',...point(e)});};
$('stream').onpointercancel=()=>{dragging=false;send({type:'release'});};
$('stream').onwheel=e=>{e.preventDefault();send({type:'zoom',delta:e.deltaY});};
for(const b of document.querySelectorAll('[data-key]')){b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);held.add(b.dataset.key);send({type:'key',key:b.dataset.key,down:true});};b.onpointerup=b.onpointercancel=()=>{held.delete(b.dataset.key);send({type:'key',key:b.dataset.key,down:false});};b.onclick=()=>send({type:'step',key:b.dataset.key});}
document.addEventListener('keydown',e=>{if(/INPUT|SELECT/.test(e.target.tagName))return;const key=e.key.toLowerCase();if(['w','a','s','d'].includes(key)){e.preventDefault();held.add(key);send({type:'key',key,down:true});}});
document.addEventListener('keyup',e=>{const key=e.key.toLowerCase();if(held.delete(key))send({type:'key',key,down:false});});
setInterval(()=>{if(held.size)send({type:'heartbeat'});},500);
function release(){held.clear();dragging=false;send({type:'release'});}window.addEventListener('blur',release);document.addEventListener('visibilitychange',()=>{if(document.hidden)release();});
$('map-wrap').onpointerup=e=>{const r=$('map-wrap').querySelector('svg')?.getBoundingClientRect();if(r)send({type:'map',x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height});};
$('fullscreen').onclick=()=>document.querySelector('.stage').requestFullscreen?.().catch(()=>notice('Rotate the phone for a larger view.'));
$('share').onclick=async()=>{const r=await fetch('/api/connection');if(!r.ok){$('pair').hidden=false;return;}const c=await r.json();$('qr').src=c.qr;$('phone-link').href=c.url;$('phone-link').textContent=c.url;$('connection-note').textContent=c.private?'Scan this QR code on a phone connected to the same Tailscale network.':'Private phone access is not configured yet. Run START-DAYLIGHT.cmd on the host.';$('connection').showModal();};$('close-share').onclick=()=>$('connection').close();
if(location.hash.length>1)pair(location.hash.slice(1)).catch(e=>{$('pair-error').textContent=e.message;});else check();
