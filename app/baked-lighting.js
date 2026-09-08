import * as T from "three";
import { EXRLoader } from "three/addons/loaders/EXRLoader.js";
import { RGBELoader } from "three/addons/loaders/RGBELoader.js";

// Irradiance is stored in a second UV set. Camera movement never rebakes it.
export class BakedLighting {
  constructor(renderer, scene, meshes) {
    this.renderer = renderer;
    this.scene = scene;
    this.meshes = meshes;
    this.current = [];
    this.ticket = 0;
    this.enabled = true;
    this.ready = false;
    this.loader = new EXRLoader();
    this.manifest = [];
  }
  async init() {
    const r = await fetch("/lightmaps/manifest.json");
    if (!r.ok) throw Error("Precomputed lighting is unavailable.");
    this.manifest = await r.json();
  }
  async load(date, time, sky) {
    const entry = this.manifest.find(
      (s) => s.date === date && s.time === time && s.sky === sky,
    );
    if (!entry) throw Error("This lighting scenario has not finished baking.");
    const ticket = ++this.ticket;
    this.ready = false;
    const rgbm = entry.encoding === "RGBM-linear";
    const loaded = await Promise.all(
      Object.entries(entry.maps).map(async ([group, url]) => {
        const tex = await (
          rgbm ? new T.TextureLoader() : this.loader
        ).loadAsync(url);
        tex.flipY = false;
        tex.channel = 1;
        tex.colorSpace = rgbm ? T.NoColorSpace : T.LinearSRGBColorSpace;
        tex.minFilter = T.LinearFilter;
        tex.magFilter = T.LinearFilter;
        tex.generateMipmaps = false;
        return [group, tex];
      }),
    );
    const probes = await Promise.all(
      Object.entries(entry.probes || {}).map(async ([region, url]) => {
        const tex = await new RGBELoader().loadAsync(url);
        tex.mapping = T.EquirectangularReflectionMapping;
        return [region, tex];
      }),
    );
    if (ticket !== this.ticket) {
      [...loaded, ...probes].forEach(([, t]) => t.dispose());
      return;
    }
    const maps = Object.fromEntries(loaded);
    for (const mesh of this.meshes) {
      const group = mesh.userData.lightmap_group;
      const m = mesh.material;
      if (mesh.userData.reflection_region)
        m.envMap =
          Object.fromEntries(probes)[mesh.userData.reflection_region] || null;
      if (group && maps[group]) {
        m.lightMap = maps[group];
        m.lightMapIntensity = Math.PI * (rgbm ? entry.ranges[group] : 1);
        // The diffuse sky and all its occlusion are already in the Cycles bake.
        // Retain the environment's specular reflections without adding diffuse twice.
        m.onBeforeCompile = (shader) => {
          let chunk = T.ShaderChunk.lights_fragment_maps.replace(
            "iblIrradiance += getIBLIrradiance( geometryNormal );",
            "",
          );
          if (rgbm)
            chunk = chunk.replace(
              "lightMapTexel.rgb * lightMapIntensity",
              "lightMapTexel.rgb * lightMapTexel.a * lightMapIntensity",
            );
          shader.fragmentShader = shader.fragmentShader.replace(
            "#include <lights_fragment_maps>",
            chunk,
          );
        };
        m.customProgramCacheKey = () => "cycles-diffuse-bake-v2-" + rgbm;
        m.needsUpdate = true;
      }
      if (mesh.userData.tree && !mesh.userData.evergreen)
        mesh.visible = !date.endsWith("12-21") && !date.endsWith("03-20");
      if (mesh.userData.spring_only) mesh.visible = false;
    }
    this.current.forEach((t) => t.dispose());
    this.current = [...loaded, ...probes].map(([, t]) => t);
    this.entry = entry;
    this.ready = true;
    this.changed = true;
  }
  render(camera) {
    this.renderer.render(this.scene, camera);
  }
}
