import fs from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=new URL('../',import.meta.url),read=p=>fs.readFileSync(new URL(p,root));
const buf=read('public/house.glb');assert.equal(buf.readUInt32LE(0),0x46546c67);assert.equal(buf.readUInt32LE(4),2);assert.equal(buf.readUInt32LE(8),buf.length);
const gltf=JSON.parse(buf.subarray(20,20+buf.readUInt32LE(12)).toString());
const glass=gltf.materials.find(m=>m.name.startsWith('Glazing'));assert(glass);assert.equal(glass.extensions.KHR_materials_transmission.transmissionFactor,1);
const mats=gltf.materials.filter(m=>m.normalTexture&&m.pbrMetallicRoughness?.baseColorTexture);assert(mats.length>=5);
const cases=JSON.parse(read('public/skies/manifest.json'));assert.equal(cases.length,12);
for(const c of cases){const hdr=read('public'+c.hdr);assert(hdr.subarray(0,100).toString().includes('FORMAT=32-bit_rle_rgbe'));assert(hdr.length>100000);if(c.sun.alt>0)assert(c.disk_alignment_error_degrees<.2);}
assert.deepEqual(JSON.parse(read('public/model.json')),JSON.parse(read('model-data.json')));
for(const name of ['study-clear','study-overcast','sunroom-clear','yard-clear','pool-clear','bath-clear','study-overcast-no-bounce','study-overcast-dark-glass','study-overcast-dark-walls','sealed-room'])assert(read('public/references/'+name+'.png').subarray(1,4).toString()==='PNG');
const report=JSON.parse(read('public/validation-results.json'));assert.equal(report.solar.length,18);assert(report.sealed_room_max_display_pixel<=1/255);
for(const [name,hash] of Object.entries(report.input_sha256))assert.equal(createHash('sha256').update(read(name)).digest('hex'),hash,'Validation inputs changed: '+name);
for(const [name,hash] of Object.entries(report.reference_sha256))assert.equal(createHash('sha256').update(read('public/references/'+name)).digest('hex'),hash,'Reference changed: '+name);
assert(buf.length<25*1024*1024,'GLB exceeds static hosting per-file budget');
console.log(JSON.stringify({glbBytes:buf.length,meshes:gltf.meshes.length,materials:gltf.materials.length,sharedTextureMaterials:mats.length,hdrScenarios:cases.length,maxSkyDirectionError:Math.max(...cases.map(c=>c.disk_alignment_error_degrees||0)),references:10,checks:'passed'},null,2));
