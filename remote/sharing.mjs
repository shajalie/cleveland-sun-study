import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn,execFile} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {normalizeEmails,validateSettings} from './sharing-auth.mjs';

export class SharingManager {
 constructor(root,{fetcher=fetch,originPort=5184,onChange=()=>{}}={}){
  this.root=root;this.runtime=path.join(root,'.runtime');this.fetcher=fetcher;this.originPort=originPort;this.onChange=onChange;
  this.config={enabled:false,emails:[]};this.job={busy:false,error:'',message:''};this.child=null;this.connected=false;
 }
 async init(){try{this.config=JSON.parse(await fs.readFile(path.join(this.runtime,'sharing.json'),'utf8'));}catch(e){if(e.code!=='ENOENT')this.job.error='Saved sharing settings could not be read. Website access remains off.';}return this;}
 async save(){await fs.mkdir(this.runtime,{recursive:true});const file=path.join(this.runtime,'sharing.json');await fs.writeFile(file+'.tmp',JSON.stringify(this.config,null,2));await fs.rename(file+'.tmp',file);this.onChange();}
 status(){const {accountId='',zoneId='',hostname='',emails=[],enabled=false}=this.config;return {accountId,zoneId,hostname,emails,enabled,connected:this.connected,configured:!!this.config.tunnelId,url:hostname?'https://'+hostname+'/':null,hasCredentials:!!this.hasCredentials,job:this.job};}
 async crypt(action,value){return new Promise((resolve,reject)=>{const child=execFile('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',path.join(this.root,'remote/protect-secret.ps1'),'-Action',action],{windowsHide:true,timeout:15000,maxBuffer:100000},(e,out)=>e?reject(Error('Windows could not unlock the saved hosting credentials for this user.')):resolve(out.trim()));child.stdin.end(value);});}
 async readSecrets(){try{const data=await fs.readFile(path.join(this.runtime,'sharing-secrets.dpapi'),'utf8');const secrets=JSON.parse(await this.crypt('unprotect',data));this.hasCredentials=!!secrets.apiToken;return secrets;}catch(e){if(e.code==='ENOENT')return {};throw e;}}
 async storeSecrets(secrets){const data=await this.crypt('protect',JSON.stringify(secrets));await fs.writeFile(path.join(this.runtime,'sharing-secrets.dpapi'),data);this.hasCredentials=!!secrets.apiToken;}
 async api(apiToken,route,method='GET',body){
  const response=await this.fetcher('https://api.cloudflare.com/client/v4'+route,{method,headers:{Authorization:'Bearer '+apiToken,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
  let data;try{data=await response.json();}catch{throw Error('Cloudflare returned an unreadable response. Sharing remains unavailable.');}
  if(!response.ok||!data.success)throw Error('Cloudflare: '+(data.errors?.map(x=>x.message).join('; ')||'request failed ('+response.status+')'));
  return data.result;
 }
 async configure(input){
  const settings=validateSettings(input);
  if(this.config.tunnelId&&['accountId','zoneId','hostname'].some(k=>settings[k]!==this.config[k]))throw Error('This copy already owns a website. Use a fresh extracted copy for another account or hostname.');
  const secrets=await this.readSecrets();if(input.apiToken)secrets.apiToken=String(input.apiToken).trim();
  if(!secrets.apiToken)throw Error('Complete the one-time Cloudflare connection below. Paste the API token into this PC dashboard only.');
  const token=secrets.apiToken,account='/accounts/'+settings.accountId;
  const zone=await this.api(token,'/zones/'+settings.zoneId);
  if(zone.account?.id!==settings.accountId||zone.status!=='active'||!settings.hostname.endsWith('.'+zone.name))throw Error('Choose an unused subdomain of an active domain in this Cloudflare account.');
  const org=await this.api(token,account+'/access/organizations');
  if(!/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(org.auth_domain||''))throw Error('Finish Cloudflare Zero Trust team setup once, then try again.');
  const existing=await this.api(token,'/zones/'+settings.zoneId+'/dns_records?name='+encodeURIComponent(settings.hostname));
  if(existing.some(r=>r.id!==this.config.dnsId))throw Error('That hostname already has a DNS record. Choose an unused name; existing websites will not be replaced.');
  this.config={...this.config,...settings,authDomain:org.auth_domain,enabled:false,instance:this.config.instance||randomUUID()};await this.save();await this.stopProcess();await this.storeSecrets(secrets);
  this.job.message='Creating email sign-in protection…';
  const providers=await this.api(token,account+'/access/identity_providers');let otp=providers.find(x=>x.type==='onetimepin');
  if(!otp)otp=await this.api(token,account+'/access/identity_providers','POST',{name:'Email login code',type:'onetimepin',config:{}});
  const policyBody={name:'Daylight '+this.config.instance,decision:'allow',include:settings.emails.map(email=>({email:{email}})),require:[{login_method:{id:otp.id}}],exclude:[],session_duration:'1h'};
  const policy=await this.api(token,account+'/access/policies'+(this.config.policyId?'/'+this.config.policyId:''),this.config.policyId?'PUT':'POST',policyBody);
  this.config.policyId=policy.id;await this.save();
  const appBody={name:'Cleveland daylight '+settings.hostname,type:'self_hosted',domain:settings.hostname,destinations:[{type:'public',uri:settings.hostname}],session_duration:'1h',allowed_idps:[otp.id],auto_redirect_to_identity:false,app_launcher_visible:false,policies:[{id:policy.id,precedence:1}]};
  const app=await this.api(token,account+'/access/apps'+(this.config.appId?'/'+this.config.appId:''),this.config.appId?'PUT':'POST',appBody);
  if(!app.id||!app.aud)throw Error('Cloudflare did not return an application identity. No tunnel will start.');
  this.config.appId=app.id;this.config.audience=app.aud;await this.save();
  this.job.message='Connecting this computer…';
  if(!this.config.tunnelId){const tunnel=await this.api(token,account+'/cfd_tunnel','POST',{name:'daylight-'+this.config.instance,config_src:'cloudflare'});if(!tunnel.id)throw Error('Tunnel creation did not return an ID.');this.config.tunnelId=tunnel.id;await this.save();}
  await this.api(token,account+'/cfd_tunnel/'+this.config.tunnelId+'/configurations','PUT',{config:{ingress:[{hostname:settings.hostname,service:'http://127.0.0.1:'+this.originPort,originRequest:{access:{required:true,teamName:org.auth_domain.split('.')[0],audTag:[app.aud]}}},{service:'http_status:404'}]}});
  if(!this.config.dnsId){const dns=await this.api(token,'/zones/'+settings.zoneId+'/dns_records','POST',{type:'CNAME',name:settings.hostname,content:this.config.tunnelId+'.cfargotunnel.com',proxied:true,ttl:1,comment:'Cleveland daylight '+this.config.instance});this.config.dnsId=dns.id;await this.save();}
  secrets.tunnelToken=await this.api(token,account+'/cfd_tunnel/'+this.config.tunnelId+'/token');if(typeof secrets.tunnelToken!=='string')throw Error('Cloudflare did not return a tunnel connection token.');await this.storeSecrets(secrets);
  this.config.enabled=true;await this.save();await this.startProcess(secrets.tunnelToken);
 }
 async updateEmails(emails){
  const next=normalizeEmails(emails);if(!this.config.policyId)throw Error('Enable website sharing first.');
  // Remove local authorization before the remote update, including open streams.
  const previous=this.config.emails;this.config.emails=previous.filter(e=>next.includes(e));await this.save();
  const secrets=await this.readSecrets();const route='/accounts/'+this.config.accountId+'/access/policies/'+this.config.policyId;
  const policy=await this.api(secrets.apiToken,route);
  await this.api(secrets.apiToken,route,'PUT',{name:policy.name,decision:'allow',include:next.map(email=>({email:{email}})),require:policy.require||[],exclude:[],session_duration:'1h'});
  this.config.emails=next;await this.save();
 }
 async startProcess(tunnelToken){
  if(this.child)return;const executable=path.join(this.root,'runtime','cloudflared.exe');await fs.access(executable).catch(()=>{throw Error('Download the latest complete Windows ZIP; its Cloudflare connector is missing.');});
  this.connected=false;this.child=spawn(executable,['tunnel','--no-autoupdate','run'],{windowsHide:true,stdio:['ignore','ignore','pipe'],env:{...process.env,TUNNEL_TOKEN:tunnelToken}});
  const child=this.child;child.stderr.on('data',chunk=>{const line=chunk.toString();if(line.includes('Registered tunnel connection')){this.connected=true;this.job.message='Website sharing is connected.';}if(line.includes('Unregistered tunnel connection'))this.connected=false;});
  child.on('error',()=>{if(this.child===child){this.child=null;this.connected=false;this.job.error='The website connector could not start.';}});
  child.on('exit',()=>{if(this.child===child){this.child=null;this.connected=false;if(this.config.enabled)this.job.error='Website connector stopped. Use Enable website sharing to reconnect.';}});
 }
 async stopProcess(){const child=this.child;this.child=null;this.connected=false;if(child){child.kill();await new Promise(resolve=>{child.once('exit',resolve);setTimeout(resolve,3000).unref();});}}
 async disable(){this.config.enabled=false;await this.save();await this.stopProcess();this.job.error='';this.job.message='Website sharing is off. Local and Moonlight use continue.';}
 async resume(){const secrets=await this.readSecrets();if(this.config.enabled&&secrets.tunnelToken)await this.startProcess(secrets.tunnelToken);}
 run(work){if(this.job.busy)throw Error('A sharing update is already running.');this.job={busy:true,error:'',message:'Preparing website sharing…'};Promise.resolve().then(work).catch(async e=>{this.job.error=e.message;if(!this.child){this.config.enabled=false;await this.save().catch(()=>{});}}).finally(()=>{this.job.busy=false;});}
}
