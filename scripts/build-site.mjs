/** Build only the connection website; the Windows host owns the 3D payload. */
import { build } from "vite";
import fs from "node:fs/promises";
import path from "node:path";

await build({
  configFile: false,
  publicDir: false,
  build: { rollupOptions: { input: "index.html" } },
});
for (const relative of [
  "validation.html",
  "validation-results.json",
  "geometry-audit.html",
  "reference-sources.json",
  "references-v2/study-clear.png",
]) {
  const target = path.join("dist", relative);
  await fs.mkdir(path.dirname(target), { recursive: true });
  await fs.copyFile(path.join("public", relative), target);
}
const files = await fs.readdir("dist/assets");
if (files.some((name) => name.startsWith("render-")))
  throw Error("Renderer must stay on the PC");
console.log("Connection website built without the 3D scene or renderer");
