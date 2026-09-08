import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";

export async function loadScene() {
  const response = await fetch("/scene/manifest.json");
  if (!response.ok) throw Error("Scene manifest unavailable");
  const manifest = await response.json(),
    parts = [];
  for (const part of manifest.parts) {
    const r = await fetch(part.url);
    if (!r.ok) throw Error("Scene data unavailable");
    const bytes = await r.arrayBuffer();
    if (bytes.byteLength !== part.bytes)
      throw Error("Incomplete scene download");
    parts.push(bytes);
  }
  const data = await new Blob(parts).arrayBuffer();
  if (data.byteLength !== manifest.bytes) throw Error("Scene size mismatch");
  return new GLTFLoader()
    .setMeshoptDecoder(MeshoptDecoder)
    .parseAsync(data, "/");
}
