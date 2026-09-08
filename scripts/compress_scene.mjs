import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { dedup, meshopt, join } from "@gltf-transform/functions";
import { MeshoptEncoder, MeshoptDecoder } from "meshoptimizer";
import fs from "node:fs/promises";
import { createHash } from "node:crypto";
await MeshoptEncoder.ready;
await MeshoptDecoder.ready;
const input = process.argv[2] || ".runtime/house-baked-raw.glb",
  output = process.argv[3] || ".runtime/house-baked.glb";
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({
    "meshopt.encoder": MeshoptEncoder,
    "meshopt.decoder": MeshoptDecoder,
  });
const doc = await io.read(input);
doc.getLogger().debug = () => {};
doc.getLogger().info = () => {};
doc.getLogger().warn = () => {};
await doc.transform(dedup());
const groupKey = (e) =>
  JSON.stringify([
    e.lightmap_group || "",
    !!e.walkable,
    !!e.detail,
    e.reflection_region || "",
  ]);
const groups = new Set(
  doc
    .getRoot()
    .listNodes()
    .filter(
      (n) => n.getMesh() && !n.getExtras().tree && !n.getExtras().spring_only,
    )
    .map((n) => groupKey(n.getExtras())),
);
for (const key of groups) {
  await doc.transform(
    join({
      filter: (n) => {
        const e = n.getExtras();
        return !e.tree && !e.spring_only && groupKey(e) === key;
      },
    }),
  );
}
await doc.transform(meshopt({ encoder: MeshoptEncoder, level: "high" }));
await io.write(output, doc);
// Sites has a per-file size limit. The host reconstructs the single GLB locally.
await fs.mkdir("public/scene", { recursive: true });
const bytes = await fs.readFile(output),
  parts = [];
for (
  let offset = 0, index = 0;
  offset < bytes.length;
  offset += 20 * 1024 * 1024, index++
) {
  const part = bytes.subarray(
      offset,
      Math.min(bytes.length, offset + 20 * 1024 * 1024),
    ),
    name = `house-${index}.bin`;
  await fs.writeFile("public/scene/" + name, part);
  parts.push({
    url: "/scene/" + name,
    bytes: part.length,
    sha256: createHash("sha256").update(part).digest("hex"),
  });
}
await fs.writeFile(
  "public/scene/manifest.json",
  JSON.stringify(
    {
      bytes: bytes.length,
      sha256: createHash("sha256").update(bytes).digest("hex"),
      parts,
    },
    null,
    2,
  ),
);
console.log(
  JSON.stringify({
    inputBytes: (await fs.stat(input)).size,
    outputBytes: (await fs.stat(output)).size,
    nodes: doc.getRoot().listNodes().length,
    materials: doc.getRoot().listMaterials().length,
  }),
);
