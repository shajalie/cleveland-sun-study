(()=>{
 const $=id=>document.getElementById(id),canvas=$('walk-canvas'),panel=$('panel-walk');
 const out=$('cleveland-sun-explorer').sunModel,inn=$('cleveland-indoor-sun').sunModel;
 const F=1200/3937,eyeHeight=1.62;
 let gl=null,program=null,buffer=null,count=0,active=false,raf=0,last=0,dirty=true,syncing=false;
 let player={x:10,y:29,z:1.62,yaw:0,pitch:0},upper=false,pressed=new Set(),lastHud=0;
 let positions=[],sceneSun={x:0,y:0,z:1},catalog=[],frameLocs={};
 function inside(p,r){let hit=false;for(let i=0,j=r.length-1;i<r.length;j=i++){const a=r[i],b=r[j];if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])hit=!hit;}return hit;}
 function cross(a,b,c){return(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);}
 function triangulate(r){let p=r.map(a=>a.slice());if(p.length>1&&Math.hypot(p[0][0]-p.at(-1)[0],p[0][1]-p.at(-1)[1])<.001)p.pop();
  const area=p.reduce((v,a,i)=>v+a[0]*p[(i+1)%p.length][1]-p[(i+1)%p.length][0]*a[1],0);if(area<0)p.reverse();
  const ids=p.map((_,i)=>i),tri=[];let guard=0;
  while(ids.length>3&&guard++<p.length*p.length){let found=false;for(let i=0;i<ids.length;i++){const ia=ids[(i+ids.length-1)%ids.length],ib=ids[i],ic=ids[(i+1)%ids.length],a=p[ia],b=p[ib],c=p[ic];if(cross(a,b,c)<1e-8)continue;
    let occupied=false;for(const id of ids){if(id===ia||id===ib||id===ic)continue;const q=p[id];if(cross(a,b,q)>=-1e-8&&cross(b,c,q)>=-1e-8&&cross(c,a,q)>=-1e-8){occupied=true;break;}}if(occupied)continue;
    tri.push([a,b,c]);ids.splice(i,1);found=true;break;
   }if(!found)break;
  }if(ids.length===3)tri.push(ids.map(i=>p[i]));return tri;
 }
 function tri(a,b,c,color){for(const p of [a,b,c])positions.push(p[0],p[1],p[2],...color);}
 function quad(a,b,c,d,color){tri(a,b,c,color);tri(a,c,d,color);}
 function flat(r,z,color){for(const t of triangulate(r))tri(...t.map(p=>[p[0],p[1],z]),color);}
 function mix(a,b,f){return a.map((v,i)=>v*(1-f)+b[i]*f);}
 const C={grass:[.32,.52,.35],deck:[.69,.68,.62],wood:[.47,.32,.20],sunwood:[.91,.72,.41],wall:[.89,.89,.85],roof:[.49,.22,.16],blue:[.12,.57,.75],green:[.16,.65,.38],trim:[.24,.19,.14]};
 function litColor(base,lit){return lit?mix(base,[1,.84,.50],.48):mix(base,[.28,.37,.45],.24);}
 function band(a,b,lo,hi,color){if(hi-lo<.005)return;quad([a[0],a[1],lo],[b[0],b[1],lo],[b[0],b[1],hi],[a[0],a[1],hi],color);}
 function holeInfo(h){const window=h.window,lo=h.sill??(window?(h.floorGlass?0:+$('ci-sill').value):0),hi=h.head??(window?+$('ci-head').value:2.15);return {lo,hi,open:window||h.alwaysOpen||$('ci-doors').value==='open'};}
 function headAt(h,t){const a=holeInfo(h),len=Math.hypot(h.b[0]-h.a[0],h.b[1]-h.a[1]),rise=Math.min(.5,len/2);return h.arch?a.hi-rise+rise*Math.sqrt(Math.max(0,1-(2*t-1)**2)):a.hi;}
 function wallMesh(w,f){const a=w.a,b=w.b,dx=b[0]-a[0],dy=b[1]-a[1],L=Math.hypot(dx,dy);if(L<.001)return;
  const holes=w.holes.map(h=>({...h,start:((h.a[0]-a[0])*dx+(h.a[1]-a[1])*dy)/L,end:((h.b[0]-a[0])*dx+(h.b[1]-a[1])*dy)/L})).map(h=>({...h,start:Math.min(h.start,h.end),end:Math.max(h.start,h.end)})).filter(h=>h.end>0&&h.start<L);
  const point=d=>[a[0]+dx*d/L,a[1]+dy*d/L];
  const cuts=[0,L];for(const h of holes){cuts.push(Math.max(0,h.start),Math.min(L,h.end));if(h.arch)for(let j=1;j<12;j++)cuts.push(h.start+(h.end-h.start)*j/12);}cuts.sort((a,b)=>a-b);
  for(let i=0;i<cuts.length-1;i++){const l=cuts[i],r=cuts[i+1],mid=(l+r)/2;if(r-l<.001)continue;const h=holes.find(h=>mid>=h.start&&mid<=h.end),pa=point(l),pb=point(r);
   if(h&&holeInfo(h).open){const q=holeInfo(h),top=headAt(h,(mid-h.start)/(h.end-h.start));band(pa,pb,f.base,f.base+q.lo,C.wall);band(pa,pb,f.base+top,f.base+f.ceiling,C.wall);}
   else band(pa,pb,f.base,f.base+f.ceiling,w.ext?C.wall:mix(C.wall,[.7,.77,.78],.12));
  }
  for(const h of holes){if(!holeInfo(h).open)continue;const q=holeInfo(h),a=point(h.start),b=point(h.end),highlight=$('walk-openings').checked,col=highlight?(h.window?C.blue:C.green):C.trim;
   const aa=point(h.start+.035),bb=point(h.end-.035);band(a,aa,f.base+q.lo,f.base+headAt(h,0),col);band(bb,b,f.base+q.lo,f.base+headAt(h,1),col);
   band(a,b,f.base+q.lo,f.base+q.lo+.025,col);
   for(let k=0;k<12;k++){const v1=k/12,v2=(k+1)/12,p1=point(h.start+(h.end-h.start)*v1),p2=point(h.start+(h.end-h.start)*v2),z1=f.base+headAt(h,v1),z2=f.base+headAt(h,v2);quad([...p1,z1-.025],[...p2,z2-.025],[...p2,z2+.025],[...p1,z1+.025],col);}
   if(h.window){const len=h.end-h.start,divs=Math.max(1,Math.round(len/.65));for(let j=1;j<divs;j++){const d=h.start+len*j/divs;band(point(d-.01),point(d+.01),f.base+q.lo,f.base+headAt(h,j/divs),col);}band(a,b,f.base+q.lo+(q.hi-q.lo)*.48,f.base+q.lo+(q.hi-q.lo)*.48+.02,col);}
  }
 }
 function ellipsoid(t,color){const n=12,m=8;const p=(i,j)=>{const lon=2*Math.PI*i/n,lat=-Math.PI/2+Math.PI*j/m;return[t.x+t.r*Math.cos(lat)*Math.cos(lon),t.y+t.r*Math.cos(lat)*Math.sin(lon),t.z+t.rz*Math.sin(lat)];};for(let j=0;j<m;j++)for(let i=0;i<n;i++)quad(p(i,j),p(i+1,j),p(i+1,j+1),p(i,j+1),mix(color,[.50,.65,.38],j/m*.2));}
 function rebuild(){if(!gl)return;positions=[];catalog=[];const O=out.state(),I=inn.state();sceneSun=out.sun(+$('walk-time').value,$('walk-date').value);
  flat([[-50,-45],[75,-45],[75,85],[-50,85]],-.08,[.38,.48,.40]);
  const parcel=O.data.parcel.map(p=>p.map(v=>v*F));flat(parcel,0,C.deck);
  for(const z of O.data.zones){const color=z.name==='Pool'?C.blue:z.name.includes('lawn')?C.grass:C.deck;flat(z.poly.map(p=>p.map(v=>v*F)),.013,color);}
  for(let i=0;i<O.samples.length;i++){const p=O.samples[i];if(p.zi>=9)continue;const base=p.zi===0?C.blue:p.zi===2||p.zi===7?C.grass:C.deck,c=litColor(base,O.current[i]===0);flat([[p.x-.4,p.y-.4],[p.x+.4,p.y-.4],[p.x+.4,p.y+.4],[p.x-.4,p.y+.4]],.027,c);}
  for(const b of O.obstacles.filter(b=>b.kind==='neighbor')){for(let j=0;j<b.poly.length;j++)band(b.poly[j],b.poly[(j+1)%b.poly.length],0,b.height,[.69,.72,.72]);flat(b.poly,b.height,[.37,.41,.43]);}
  for(const f of I.data.floors){
   flat(f.outline,f.base,C.wood);flat(f.outline,f.base+f.ceiling,C.wall);
   for(const wall of f.walls){wallMesh(wall,f);if(wall.ext){catalog.push({wall,f});if(f===I.data.floors[0])band(wall.a,wall.b,0,f.base,[.70,.71,.65]);if(f===I.data.floors[1])band(wall.a,wall.b,f.base+f.ceiling,7.45,C.wall);}else catalog.push({wall,f});}
  }
  // The active floor uses the same ray/window model as the indoor plan.
  for(let i=0;i<I.samples.length;i++){const p=I.samples[i],c=litColor(C.wood,I.current[i]===0);flat([[p.x-.17,p.y-.17],[p.x+.17,p.y-.17],[p.x+.17,p.y+.17],[p.x-.17,p.y+.17]],I.floor.base+.03,c);}
  for(const b of O.obstacles.filter(b=>b.kind==='porch')){flat(b.poly,b.height,[.87,.87,.82]);for(const p of b.poly.slice(0,-1)){const r=.12;flat([[p[0]-r,p[1]-r],[p[0]+r,p[1]-r],[p[0]+r,p[1]+r],[p[0]-r,p[1]+r]],b.height,C.wall);band([p[0]-.1,p[1]],[p[0]+.1,p[1]],0,b.height,C.wall);}}
  const main=O.obstacles.find(b=>b.kind==='main'),r=main.poly,cx=r.reduce((n,p)=>n+p[0],0)/r.length,cy=r.reduce((n,p)=>n+p[1],0)/r.length,inner=r.map(p=>[cx+(p[0]-cx)*.55,cy+(p[1]-cy)*.6]);
  for(let i=0;i<r.length;i++)quad([...r[i],7.45],[...r[(i+1)%r.length],7.45],[...inner[(i+1)%r.length],9],[...inner[i],9],C.roof);flat(inner,9,[.83,.81,.75]);
  for(const b of O.obstacles.filter(b=>b.kind==='wing'))flat(b.poly,7.45,[.86,.86,.81]);
  if($('walk-trees').checked)for(const t of O.trees){ellipsoid(t,[.24,.43,.28]);band([t.x-.11,t.y],[t.x+.11,t.y],0,t.z,[.29,.24,.17]);band([t.x,t.y-.11],[t.x,t.y+.11],0,t.z,[.29,.24,.17]);}
  const ss={x:10+sceneSun.x*80,y:20+sceneSun.y*80,z:sceneSun.z*80,r:1.2,rz:1.2};if(sceneSun.z>0)ellipsoid(ss,[1,.94,.64]);
  gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(positions),gl.STATIC_DRAW);count=positions.length/6;dirty=false;
 }
 function init(){gl=canvas.getContext('webgl',{antialias:true,alpha:false});if(!gl){$('walk-error').hidden=false;return false;}
  const vertex='attribute vec3 aPosition;attribute vec3 aColor;uniform vec3 uEye,uRight,uUp,uForward;uniform float uAspect,uTan,uDay;varying vec3 vColor;void main(){vec3 r=aPosition-uEye;float z=dot(r,uForward);gl_Position=vec4(dot(r,uRight)/(uTan*uAspect),dot(r,uUp)/uTan,1.000667*z-0.100033,z);vColor=aColor*uDay;}';
  const fragment='precision mediump float;varying vec3 vColor;void main(){gl_FragColor=vec4(vColor,1.0);}';
  function shader(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
  try{program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('3D program failed');gl.useProgram(program);buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
   for(const [name,offset] of [['aPosition',0],['aColor',12]]){const loc=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,24,offset);}for(const name of ['uEye','uRight','uUp','uForward','uAspect','uTan','uDay'])frameLocs[name]=gl.getUniformLocation(program,name);gl.enable(gl.DEPTH_TEST);return true;
  }catch(e){$('walk-error').hidden=false;console.error(e);return false;}
 }
 function floorNow(){return inn.state().data.floors[upper?1:0];}
 function canMove(x,y){const f=floorNow();if(upper&&!inside([x,y],f.outline))return false;if(x< -5||x>28||y< -5||y>43)return false;
  const pool=out.state().data.zones[0].poly.map(p=>p.map(v=>v*F));if(!upper&&inside([x,y],pool))return false;
  for(const wall of f.walls){const a=wall.a,b=wall.b,dx=b[0]-a[0],dy=b[1]-a[1],len=dx*dx+dy*dy,t=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/len));if(Math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)>.18)continue;
   let pass=false;for(const hole of wall.holes){const hx=hole.b[0]-hole.a[0],hy=hole.b[1]-hole.a[1],L=Math.hypot(hx,hy),u=((x-hole.a[0])*hx+(y-hole.a[1])*hy)/(L*L),q=holeInfo(hole);if(u>.18/L&&u<1-.18/L&&q.lo<.1&&q.open&&(!hole.window||hole.floorGlass)){pass=true;break;}}if(!pass)return false;
  }return true;
 }
 function spawn(){const n=$('walk-start').value,floors=inn.state().data.floors;upper=n==='primary'||n==='sunroom';const idx=upper?'1':'0';if($('ci-floor').value!==idx){$('ci-floor').value=idx;$('ci-floor').dispatchEvent(new Event('change'));}
  const room=(i,name)=>floors[i].rooms.find(r=>r.name===name).label;
  const starts={yard:[10.8,34,Math.PI],terrace:[14,29,0],front:[9,6,0],foyer:[...room(0,'Foyer'),0],study:[...room(0,'Study'),0],primary:[...room(1,'Primary bedroom'),0],sunroom:[...room(1,'Sunroom'),0]};const a=starts[n];player.x=a[0];player.y=a[1];player.yaw=a[2];player.pitch=-.08;setHeight();dirty=true;
 }
 function setHeight(){const f=floorNow(),isIn=inside([player.x,player.y],f.outline);player.z=(upper?f.base:isIn?f.base:0)+eyeHeight;}
 function sync(){if(syncing)return;syncing=true;const date=$('walk-date').value,time=$('walk-time').value;if(!date){syncing=false;return;}
  for(const prefix of ['cs','ci']){$(prefix+'-date').value=date;$(prefix+'-time').value=time;$(prefix+'-canopy').value=$('walk-trees').checked?'full':'none';}out.update();inn.update();dirty=true;syncing=false;
 }
 function hud(){const f=floorNow(),room=inside([player.x,player.y],f.outline)?f.rooms.find(r=>inside([player.x,player.y],r.poly)):null;$('walk-location').textContent=room?(upper?'Second · ':'Main · ')+room.name:'Outside';
  drawMini(room);const s=sceneSun,shade=room?inn.state().indoorShade({x:player.x,y:player.y,z:player.z-f.base},s):out.shade({x:player.x,y:player.y,z:player.z},s);$('walk-light').textContent=shade===0?'Direct sun at eye level':shade===3?'Sun below horizon':shade===2?'Tree shade at eye level':'No direct sun at eye level';
  const m=+$('walk-time').value,hr=Math.floor(m/60);$('walk-clock').textContent=`${hr%12||12}:${String(m%60).padStart(2,'0')} ${hr>=12?'PM':'AM'} ${s.tz||'EDT'}`;
 }
 function drawMini(room){const c=$('walk-mini'),ctx=c.getContext('2d');if(!ctx)return;const O=out.state(),f=floorNow(),r=room?f.outline:O.data.parcel.map(p=>p.map(v=>v*F));const xs=r.map(p=>p[0]),ys=r.map(p=>p[1]),loX=Math.min(...xs),hiX=Math.max(...xs),loY=Math.min(...ys),hiY=Math.max(...ys),scale=Math.min(116/(hiX-loX),132/(hiY-loY)),X=x=>70+(x-(hiX+loX)/2)*scale,Y=y=>80-(y-(hiY+loY)/2)*scale;ctx.clearRect(0,0,140,160);ctx.lineWidth=1;ctx.strokeStyle='#657b89';ctx.fillStyle='#e5edf1';ctx.beginPath();r.forEach((p,i)=>i?ctx.lineTo(X(p[0]),Y(p[1])):ctx.moveTo(X(p[0]),Y(p[1])));ctx.closePath();ctx.fill();ctx.stroke();for(const wall of f.walls){ctx.strokeStyle='#657b89';ctx.beginPath();ctx.moveTo(X(wall.a[0]),Y(wall.a[1]));ctx.lineTo(X(wall.b[0]),Y(wall.b[1]));ctx.stroke();if(room)for(const hole of wall.holes){ctx.strokeStyle=hole.window?'#2d8dbc':'#3f8059';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(X(hole.a[0]),Y(hole.a[1]));ctx.lineTo(X(hole.b[0]),Y(hole.b[1]));ctx.stroke();ctx.lineWidth=1;}}const x=X(player.x),y=Y(player.y);ctx.fillStyle='#d97718';ctx.beginPath();ctx.arc(x,y,3.5,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#d97718';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+Math.sin(player.yaw)*11,y-Math.cos(player.yaw)*11);ctx.stroke();}
 function frame(t){if(!active)return;const dt=Math.min(.05,(t-last)/1000||.016);last=t;
  let f=(pressed.has('forward')?1:0)-(pressed.has('back')?1:0),r=(pressed.has('right')?1:0)-(pressed.has('left')?1:0),norm=Math.hypot(f,r)||1;f/=norm;r/=norm;
  const speed=2.0*dt,dx=(Math.sin(player.yaw)*f+Math.cos(player.yaw)*r)*speed,dy=(Math.cos(player.yaw)*f-Math.sin(player.yaw)*r)*speed;
  if(canMove(player.x+dx,player.y))player.x+=dx;if(canMove(player.x,player.y+dy))player.y+=dy;setHeight();
  if(dirty)rebuild();const d=Math.min(2,devicePixelRatio||1),ww=Math.max(1,Math.round(canvas.clientWidth*d)),hh=Math.max(1,Math.round(canvas.clientHeight*d));if(canvas.width!==ww||canvas.height!==hh){canvas.width=ww;canvas.height=hh;}gl.viewport(0,0,ww,hh);
  const daylight=sceneSun.z>0?1:.2;gl.clearColor(.74*daylight,.85*daylight,.93*daylight,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  const sy=Math.sin(player.yaw),cy=Math.cos(player.yaw),sp=Math.sin(player.pitch),cp=Math.cos(player.pitch);gl.uniform3f(frameLocs.uEye,player.x,player.y,player.z);gl.uniform3f(frameLocs.uRight,cy,-sy,0);gl.uniform3f(frameLocs.uUp,-sy*sp,-cy*sp,cp);gl.uniform3f(frameLocs.uForward,sy*cp,cy*cp,sp);gl.uniform1f(frameLocs.uAspect,ww/hh);gl.uniform1f(frameLocs.uTan,Math.tan(Math.PI*35/180));gl.uniform1f(frameLocs.uDay,daylight);gl.drawArrays(gl.TRIANGLES,0,count);if(t-lastHud>160){hud();lastHud=t;}raf=requestAnimationFrame(frame);
 }
 let drag=null;canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,yaw:player.yaw,pitch:player.pitch};canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',e=>{if(!drag)return;player.yaw=drag.yaw+(e.clientX-drag.x)*.006;player.pitch=Math.max(-1.25,Math.min(1.25,drag.pitch-(e.clientY-drag.y)*.006));});canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
 const keyMap={w:'forward',ArrowUp:'forward',s:'back',ArrowDown:'back',a:'left',ArrowLeft:'left',d:'right',ArrowRight:'right'};window.addEventListener('keydown',e=>{if(!active||/INPUT|SELECT|TEXTAREA/.test(e.target.tagName))return;const k=keyMap[e.key];if(k){e.preventDefault();pressed.add(k);}});window.addEventListener('keyup',e=>{const k=keyMap[e.key];if(k)pressed.delete(k);});window.addEventListener('blur',()=>pressed.clear());
 document.querySelectorAll('[data-move]').forEach(b=>{b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);pressed.add(b.dataset.move);};b.onpointerup=b.onpointercancel=()=>pressed.delete(b.dataset.move);});
 $('walk-start').onchange=spawn;$('walk-restart').onclick=spawn;$('walk-date').onchange=sync;let timeJob=0;$('walk-time').oninput=()=>{clearTimeout(timeJob);timeJob=setTimeout(sync,80);};$('walk-trees').onchange=sync;$('walk-openings').onchange=()=>dirty=true;
 document.addEventListener('sunmodelchange',()=>dirty=true);
 window.ClevelandWalk={activate(){if(active)return;if(!gl&&!init())return;active=true;sync();spawn();raf=requestAnimationFrame(frame);},pause(){active=false;cancelAnimationFrame(raf);pressed.clear();},diagnostics(){return{vertices:count,finite:positions.every(Number.isFinite),player:{...player},active};}};
})();
