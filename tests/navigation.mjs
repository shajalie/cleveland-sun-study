import assert from 'node:assert/strict';
import fs from 'node:fs';
import {Navigation} from '../app/navigation.js';

const data=JSON.parse(fs.readFileSync('public/model-realism.json'));
const obstacles=JSON.parse(fs.readFileSync('public/collision-realism.json'));
const navigation=new Navigation(data,obstacles);
assert(navigation.safe(14.55,19.5,0),'Living room starting position must be reachable');
assert(!navigation.safe(5,32,0),'Pool must block walking');
assert(!navigation.safe(10,37.1,0),'Rear privacy fence must block walking');
assert(!navigation.safe(25,20,0),'Outside parcel must block walking');
assert(!navigation.safe(4.359,18,0),'Opaque exterior wall must block walking');
assert(!navigation.safe(12,10,1),'Upper floor cannot extend over garden');
assert(!navigation.safe(NaN,20,0));
assert.equal(navigation.ground(14.55,19.5,0),data.indoor.floors[0].base);
assert.equal(navigation.ground(14.55,19.5,1),data.indoor.floors[1].base);
assert.equal(navigation.ground(10.6,12,0),.8,'Raised porch must match camera height');
for(const floor of data.indoor.floors){
  for(const room of floor.rooms){
    const level=data.indoor.floors.indexOf(floor);
    assert(navigation.nearest(...room.label,level),`No reachable destination for ${room.name}`);
  }
}
console.log('Navigation: rooms, floors, walls, fence, pool, porch, invalid input passed');
