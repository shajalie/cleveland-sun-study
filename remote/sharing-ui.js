(()=>{
 const el=id=>document.getElementById(id);let info,timer;
 async function refresh(){const r=await fetch('/api/sharing');if(!r.ok){el('sharing-admin').hidden=true;el('sharing-viewer').hidden=false;return false;}info=await r.json();el('sharing-admin').hidden=false;el('sharing-viewer').hidden=true;
 for(const [id,key] of [['cf-account','accountId'],['cf-zone','zoneId'],['cf-hostname','hostname']]){if(document.activeElement!==el(id)&&!el(id).value)el(id).value=info[key];el(id).disabled=info.configured;}
 if(document.activeElement!==el('allowed-emails')&&!el('allowed-emails').value)el('allowed-emails').value=info.emails.join('\n');
 el('cloudflare-setup').open=!info.configured;el('enable-website').disabled=info.job.busy;el('save-emails').disabled=!info.configured||info.job.busy;el('disable-website').disabled=!info.enabled||info.job.busy;
 el('sharing-status').textContent=info.job.error||(info.job.busy?info.job.message:info.connected?'Website connected. Only the listed emails can sign in.':info.enabled?'Connecting to the website…':'Website sharing is off.');
 el('sharing-link-box').hidden=!info.enabled;if(info.enabled){el('email-website-link').href=info.url;el('email-website-link').textContent=info.url;el('email-qr').src='/api/sharing-qr';}
 return info.job.busy||(info.enabled&&!info.connected);
 }
 function poll(){clearInterval(timer);timer=setInterval(async()=>{try{if(!await refresh())clearInterval(timer);}catch{clearInterval(timer);}},1500);}
 async function send(action){try{const b={action,emails:el('allowed-emails').value};if(action==='enable')Object.assign(b,{accountId:el('cf-account').value,zoneId:el('cf-zone').value,hostname:el('cf-hostname').value,apiToken:el('cf-token').value});const r=await fetch('/api/sharing',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});el('cf-token').value='';if(!r.ok)throw Error((await r.json()).error);await refresh();poll();}catch(e){el('sharing-status').textContent=e.message;}}
 el('share').addEventListener('click',()=>{refresh().then(b=>{if(b)poll();}).catch(()=>{});});
 el('enable-website').onclick=()=>send('enable');el('disable-website').onclick=()=>send('disable');el('save-emails').onclick=()=>send('emails');
 el('copy-email-link').onclick=()=>navigator.clipboard.writeText(info.url).then(()=>el('sharing-status').textContent='Website link copied. Only the listed emails can sign in.').catch(()=>el('sharing-status').textContent='Select the website link to copy it.');
})();