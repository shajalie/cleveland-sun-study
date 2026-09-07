import {createRemoteJWKSet,jwtVerify} from 'jose';

export function normalizeEmails(value){
 const items=Array.isArray(value)?value:String(value||'').split(/[\s,;]+/);
 const emails=[...new Set(items.map(x=>String(x).trim().toLowerCase()).filter(Boolean))];
 if(!emails.length||emails.length>50||emails.some(x=>x.length>254||!/^[^\s@*]+@[^\s@*]+\.[^\s@*]+$/.test(x)))throw Error('Enter 1–50 individual email addresses. Domains and wildcards are not allowed.');
 return emails;
}
export function validateSettings(input){
 const accountId=String(input.accountId||'').trim(),zoneId=String(input.zoneId||'').trim();
 const hostname=String(input.hostname||'').trim().toLowerCase();
 if(!/^[a-f0-9]{32}$/.test(accountId)||!/^[a-f0-9]{32}$/.test(zoneId))throw Error('Enter the Cloudflare account ID and domain zone ID.');
 if(hostname.length>253||!/^([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(hostname))throw Error('Enter a hostname such as daylight.yourdomain.com, without https:// or a path.');
 return {accountId,zoneId,hostname,emails:normalizeEmails(input.emails)};
}
export function createAccessVerifier(getConfig,{resolveKeys}={}){
 let issuerCache='',keys;
 return async request=>{
  const c=getConfig();
  if(!c.enabled||!c.audience||!c.authDomain||!c.hostname)throw Error('Website sharing is off.');
  if(!/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(c.authDomain))throw Error('Invalid authentication configuration.');
  if(request.headers.host!==c.hostname&&request.headers.host!==c.hostname+':443')throw Error('Wrong website hostname.');
  const assertion=request.headers['cf-access-jwt-assertion'];
  if(typeof assertion!=='string'||assertion.length>16384)throw Error('Email sign-in is required.');
  const issuer='https://'+c.authDomain;
  if(issuerCache!==issuer){issuerCache=issuer;keys=resolveKeys||createRemoteJWKSet(new URL(issuer+'/cdn-cgi/access/certs'),{timeoutDuration:5000,cooldownDuration:30000});}
  const {payload}=await jwtVerify(assertion,keys,{issuer,audience:c.audience,algorithms:['RS256'],requiredClaims:['exp','iat','sub','email']});
  const email=typeof payload.email==='string'?payload.email.toLowerCase():'';
  if(!c.emails.includes(email))throw Error('This email is not on the allowed list.');
  return {email,expires:payload.exp};
 };
}
