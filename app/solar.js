import SunCalc from 'suncalc';
export function localInstant(date,minutes){
 const [y,m,d]=date.split('-').map(Number);const nominal=Date.UTC(y,m-1,d,Math.floor(minutes/60),minutes%60);
 const fmt=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',timeZoneName:'shortOffset'});
 const offset=t=>{const s=fmt.formatToParts(new Date(t)).find(p=>p.type==='timeZoneName').value;return Number(s.replace('GMT',''))||0;};
 let utc=nominal-offset(nominal)*3600000;utc=nominal-offset(utc)*3600000;return new Date(utc);
}
export function solar(date,minutes,data){
 const instant=localInstant(date,minutes);const p=SunCalc.getPosition(instant,data.lat,data.lon);const az=p.azimuth+Math.PI;const up=Math.sin(p.altitude),east=Math.sin(az)*Math.cos(p.altitude),north=Math.cos(az)*Math.cos(p.altitude);
 return {x:east*data.ux[0]+north*data.ux[1],y:east*data.uy[0]+north*data.uy[1],z:up,alt:p.altitude*180/Math.PI,az:(az*180/Math.PI+360)%360,instant:instant.toISOString(),clock:new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(instant)};
}
