import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import {fileURLToPath} from 'node:url';
import {SharingManager} from '../remote/sharing.mjs';
const root=fileURLToPath(new URL('..',import.meta.url));
const host=JSON.parse(await fs.readFile(new URL('../.runtime/host.json',import.meta.url),'utf8'));
const port=Number(process.env.DAYLIGHT_SHARING_PORT||5184);
const base='http://127.0.0.1:'+port;
for(const endpoint of ['/','/api/state','/api/connect','/api/sharing','/api/connection','/client.js']){
 const response=await fetch(base+endpoint,{headers:{Cookie:'daylight='+host.token,'Cf-Access-Authenticated-User-Email':'owner@example.com','Cf-Access-Jwt-Assertion':'forged.jwt.token'}});
 assert.equal(response.status,403,endpoint+' must not accept legacy pairing credentials or forged identity headers');
}
const r=await new Promise((resolve,reject)=>{const req=http.request('http://127.0.0.1:'+host.port+'/api/sharing',{headers:{Host:'remote.example',Cookie:'daylight='+host.token}},res=>{res.resume();resolve(res.statusCode);});req.on('error',reject);req.end();});assert.equal(r,403);
const manager=new SharingManager(root),plain='nonsecret-test-value-'+Date.now();
const protectedValue=await manager.crypt('protect',plain);assert(!protectedValue.includes(plain));assert.equal(await manager.crypt('unprotect',protectedValue),plain);
console.log(JSON.stringify({separateWebsiteListenerFailsClosed:true,pairingCannotBypassEmailLogin:true,remoteSharingAdministrationRejected:true,windowsCredentialEncryptionRoundTrip:true},null,2));
