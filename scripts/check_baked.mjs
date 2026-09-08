import fs from "node:fs";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
const read = (p) => fs.readFileSync(p),
  sha = (b) => createHash("sha256").update(b).digest("hex");
const manifest = JSON.parse(read("public/scene/manifest.json"));
const data = Buffer.concat(
  manifest.parts.map((p) => {
    const b = read("public" + p.url);
    assert.equal(b.length, p.bytes);
    assert.equal(sha(b), p.sha256);
    assert(b.length <= 25 * 1024 * 1024);
    return b;
  }),
);
assert.equal(data.length, manifest.bytes);
assert.equal(sha(data), manifest.sha256);
assert.equal(data.readUInt32LE(0), 0x46546c67);
const gltf = JSON.parse(data.subarray(20, 20 + data.readUInt32LE(12)));
for (const prefix of [
  "Plaster",
  "Cognac leather",
  "Natural linen curtains",
  "Modeled terracotta clay",
  "Dark charcoal painted privacy fence",
  // The exporter deduplicates the identical paving and garden-wall material.
  "Pale stone garden walls",
]) {
  const material = gltf.materials.find((m) => m.name?.startsWith(prefix));
  assert(material?.normalTexture, `${prefix} lost its surface normal texture`);
  assert(
    material.pbrMetallicRoughness?.metallicRoughnessTexture,
    `${prefix} lost roughness`,
  );
}
assert(
  gltf.meshes.some((m) => m.primitives.some((p) => "COLOR_0" in p.attributes)),
  "Natural vertex color variation is missing",
);
assert(
  gltf.nodes.some((n) => n.name?.startsWith("Privacy")),
  "Fence is missing",
);
const trees = gltf.nodes.filter((n) => n.extras?.tree);
assert(trees.length >= 14, "Missing vegetation");
assert(trees.some((n) => n.extras.evergreen));
assert(trees.some((n) => !n.extras.evergreen));
for (const n of gltf.nodes.filter(
  (n) => n.extras?.lightmap_group && n.mesh !== undefined,
))
  for (const p of gltf.meshes[n.mesh].primitives)
    assert("TEXCOORD_1" in p.attributes, "Missing lightmap coordinates");
const skies = JSON.parse(read("public/skies/manifest.json")),
  cases = JSON.parse(read("public/lightmaps/manifest.json"));
assert.equal(cases.length, 24);
assert.equal(new Set(cases.map((c) => c.key)).size, 24);
const sceneSha256 = sha(read("cleveland-bake.blend"));
const nativePresets = JSON.parse(read("public/native-presets/manifest.json"));
assert.equal(nativePresets.sceneSha256, sha(read("cleveland-realism.blend")));
assert.equal(
  nativePresets.pipelineSha256,
  sha(
    Buffer.concat([
      read("remote/cycles_worker.py"),
      read("scripts/rendering.py"),
    ]),
  ),
);
assert.equal(nativePresets.views.length, 6);
for (const view of nativePresets.views)
  assert.equal(view.sha256, sha(read("public/native-presets/" + view.file)));
for (const s of skies)
  for (const sky of ["clear", "overcast"]) {
    const c = cases.find(
      (c) => c.date === s.date && c.time === s.time && c.sky === sky,
    );
    assert(c);
    assert.equal(c.sceneSha256, sceneSha256);
    assert.equal(c.resolution, 2048);
    assert(c.samples >= 96);
    assert.equal(c.encoding, "RGBM-linear");
    assert.equal(c.denoiser, "OIDN HDR");
    for (const [group, url] of Object.entries(c.maps)) {
      const b = read("public" + url);
      assert.equal(b.subarray(1, 4).toString(), "PNG");
      assert.equal(b.readUInt32BE(16), 2048);
      assert.equal(b.readUInt32BE(20), 2048);
      assert(c.ranges[group] > 0);
    }
    for (const region of ["lower", "upper"]) {
      const b = read("public" + c.probes[region]);
      assert(b.subarray(0, 100).toString().includes("FORMAT=32-bit_rle_rgbe"));
    }
  }
const collisions = JSON.parse(read("public/collision-realism.json"));
assert.equal(
  collisions.filter((c) => c.name === "Privacy fence barrier").length,
  3,
);
for (const name of [
  "study-clear",
  "study-overcast",
  "sunroom-clear",
  "yard-clear",
  "pool-clear",
  "bath-clear",
])
  assert.equal(
    read("public/references-v2/" + name + ".png")
      .subarray(1, 4)
      .toString(),
    "PNG",
  );
const report = {
  testedAt: new Date().toISOString(),
  scenarioCount: cases.length,
  sceneSha256,
  sceneBytes: data.length,
  sceneNodes: gltf.nodes.length,
  treeNodes: trees.length,
  materials: gltf.materials.length,
  bakeSeconds: cases.reduce((s, c) => s + c.seconds, 0),
  medianScenarioSeconds: cases.map((c) => c.seconds).sort((a, b) => a - b)[12],
  checks: [
    "All 24 scenarios match the same prepared scene",
    "Scene chunks and complete GLB hashes verified",
    "Every baked mesh has a second UV set",
    "Plaster, leather, fabric, roof, fence and stone retain normal and roughness maps",
    "Two local reflection probes per scenario",
    "Evergreen and deciduous vegetation and three fence collision barriers present",
    "Six independent Cycles reference renders present",
  ],
  limitations: [
    "Geometry and material reflectance are photo-informed estimates, not a measured replica",
    "Baked diffuse light and static reflection probes approximate view-dependent transport",
    "Existing plan discrepancy remains: living depth about 8.4 m versus listing label 7.62 m",
  ],
};
fs.writeFileSync(
  "realism-validation.json",
  JSON.stringify(report, null, 2) + "\n",
);
console.log(JSON.stringify(report, null, 2));
