import fs from 'node:fs';
import {solar} from '../app/solar.js';
const d=JSON.parse(fs.readFileSync(new URL('../model-data.json',import.meta.url))).indoor;
const scenarios=[];
for(const date of ['2026-03-20','2026-06-21','2026-09-22','2026-12-21','2027-03-14','2027-11-07'])for(const time of [540,780,1020]){const sun=solar(date,time,d);scenarios.push({date,time,sun});}
fs.writeFileSync(new URL('../public/scenarios.json',import.meta.url),JSON.stringify(scenarios,null,2));
