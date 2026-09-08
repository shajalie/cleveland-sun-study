import "./style.css";
import * as T from "three";
import { RGBELoader } from "three/addons/loaders/RGBELoader.js";
import { loadScene } from "./load-scene.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  WebGLPathTracer,
  GradientEquirectTexture,
  DenoiseMaterial,
} from "three-gpu-pathtracer";
import { FullScreenQuad } from "three/addons/postprocessing/Pass.js";
import { solar } from "./solar.js";
import { BakedLighting } from "./baked-lighting.js";
import { Navigation, inside, meters } from "./navigation.js";
let navigation;
const $ = (id) => document.getElementById(id),
  F = 1200 / 3937,
  canvas = $("scene");
let data,
  house,
  pt,
  renderer,
  scene,
  camera,
  orbit,
  sun,
  skyTex,
  meshes = [],
  trees = [],
  glasses = [],
  blocks = [],
  mode = "appearance",
  sky = "clear",
  level = 0,
  view = "walk",
  siteMap = false,
  ready = false,
  yaw = 0,
  pitch = -0.09,
  last = 0,
  drag = null,
  lastMove = 0,
  toastTimer,
  lastHud = 0;
const keys = new Set(),
  player = { x: 14.55, y: 19.5 },
  ray = new T.Raycaster(),
  pointer = new T.Vector2(),
  v = new T.Vector3(),
  places = [];
let ss,
  light,
  mapTransform,
  canopyScale = 1,
  skyCases = [],
  skyTicket = 0,
  quality = 0,
  baked,
  livePT,
  fast = true,
  renderFrames = 0,
  fps = 0,
  fpsStart = 0,
  dirty = true,
  revision = 0;
const hdrCache = new Map();
function sunDirection() {
  if (!ss) return;
  const rel = Math.atan2(
    Math.sin(Math.atan2(ss.x, ss.y) - yaw),
    Math.cos(Math.atan2(ss.x, ss.y) - yaw),
  );
  const side =
    Math.abs(rel) > 2.35
      ? "behind you"
      : Math.abs(rel) < 0.78
        ? "ahead"
        : rel > 0
          ? "to your right"
          : "to your left";
  $("sun-direction").textContent =
    ss.alt <= 0
      ? "☾ Below horizon"
      : sky === "overcast"
        ? "☁ Diffuse sky"
        : `☀ Sun ${side} · ${Math.round(ss.alt)}° up`;
}
function toast(text) {
  $("toast").textContent = text;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("toast").hidden = true), 2600);
}
function fNow(l = level) {
  return data.indoor.floors[l];
}
function ground(x, y, l = level) {
  return navigation.ground(x, y, l);
}
function safe(x, y, l = level) {
  return navigation.safe(x, y, l);
}
function nearest(x, y, l = level) {
  return navigation.nearest(x, y, l);
}
function pose() {
  camera.position.set(player.x, ground(player.x, player.y) + 1.62, -player.y);
  camera.lookAt(
    player.x + Math.sin(yaw) * Math.cos(pitch),
    camera.position.y + Math.sin(pitch),
    -player.y - Math.cos(yaw) * Math.cos(pitch),
  );
  camera.updateMatrixWorld();
  pt?.updateCamera();
  lastMove = performance.now();
  updateLocation();
  drawMap();
  sunDirection();
}
function setView(value) {
  hideReference();
  view = value;
  orbit.enabled = value === "orbit";
  $("walk").setAttribute("aria-pressed", value === "walk");
  $("orbit").setAttribute("aria-pressed", value === "orbit");
  $("pad").hidden = value !== "walk";
  if (value === "orbit") {
    orbit.target.set(player.x, ground(player.x, player.y) + 1, -player.y);
    camera.position.set(player.x + 21, 22, -player.y + 20);
    orbit.update();
    pt.updateCamera();
  } else pose();
  $("view-hint").textContent =
    value === "walk"
      ? "Drag to look · tap to move · WASD / arrow keys to walk"
      : "Drag to orbit · wheel / pinch to zoom · tap ground to enter";
}
function teleport(x, y, l = level, adjust = false) {
  hideReference();
  const dest = adjust ? nearest(x, y, l) : safe(x, y, l) ? [x, y] : null;
  if (!dest) {
    toast("Choose clear floor or ground. Pool and planting are off limits.");
    return false;
  }
  level = l;
  player.x = dest[0];
  player.y = dest[1];
  if (view !== "walk") setView("walk");
  pose();
  syncFloor();
  if (innerWidth < 761) hidePanel(true);
  return true;
}
function syncFloor() {
  $("main-floor").setAttribute("aria-pressed", level === 0);
  $("second-floor").setAttribute("aria-pressed", level === 1);
  drawMap();
}
function switchFloor(l) {
  siteMap = false;
  let p = nearest(player.x, player.y, l);
  if (!p || !inside(p, fNow(l).outline))
    p = nearest(...fNow(l).rooms.at(-1).label, l);
  if (p) teleport(...p, l, true);
}
function updateLocation() {
  const r = fNow().rooms.find((r) => inside([player.x, player.y], r.poly));
  const outdoor = data.outdoor.zones.find((z) =>
    inside([player.x, player.y], meters(z.poly)),
  );
  $("location").textContent = r
    ? (level ? "Second · " : "Main · ") + r.name
    : outdoor?.name.replace(" (inferred edges)", "") || "Garden path";
  const idx = places.findIndex(
    (p) =>
      p.level === level &&
      (r
        ? p.name === r.name
        : p.name === outdoor?.name.replace(" (inferred edges)", "")),
  );
  if (idx >= 0) $("places").value = String(idx);
}
async function updateLighting() {
  if (ready) hideReference();
  const ticket = ++skyTicket,
    kind = sky;
  ss = solar($("date").value, +$("time").value, data.indoor);
  const c = skyCases.find(
    (c) => c.date === $("date").value && c.time === +$("time").value,
  );
  if (!c) return;
  sun.position.set(10 + ss.x * 100, ss.z * 100, -20 - ss.y * 100);
  sun.target.position.set(10, 0, -20);
  sun.target.updateMatrixWorld();
  sun.intensity = mode === "direct" && sky === "clear" && ss.alt > 0 ? 3 : 0;
  $("clock").textContent = ss.clock;
  $("sun-info").textContent =
    ss.alt > 0
      ? "Sun " +
        Math.round(ss.alt) +
        "° above horizon · " +
        Math.round(ss.az) +
        "° compass bearing" +
        (sky === "overcast" ? " · diffuse only" : "") +
        ($("date").value.includes("-12-")
          ? " · compare leaf-off trees below"
          : "")
      : "Sun below the horizon";
  $("render-state").textContent = "Loading atmospheric sky…";
  let tex;
  if (kind === "clear") {
    if (!hdrCache.has(c.hdr) && hdrCache.size >= 2) {
      const oldest = hdrCache.keys().next().value;
      hdrCache.get(oldest).then((t) => {
        if (t !== skyTex) t.dispose();
      });
      hdrCache.delete(oldest);
    }
    if (!hdrCache.has(c.hdr))
      hdrCache.set(c.hdr, new RGBELoader().loadAsync(c.hdr));
    tex = await hdrCache.get(c.hdr);
    tex.mapping = T.EquirectangularReflectionMapping;
  } else {
    tex = new GradientEquirectTexture(256);
    tex.generationCallback = (polar, uv, coord, color) => {
      const up = Math.cos(polar.phi),
        v = up > 0 ? (c.overcast_zenith * (1 + 2 * up)) / 3 : 0;
      return color.setRGB(v, v, v);
    };
    tex.update();
  }
  if (ticket !== skyTicket) {
    if (kind === "overcast") tex.dispose();
    return;
  }
  const old = skyTex;
  skyTex = tex;
  scene.environment = tex;
  scene.background = tex;
  scene.environmentIntensity = mode === "direct" ? 0 : 1;
  scene.backgroundIntensity = 1;
  if (livePT) {
    livePT.updateEnvironment();
    livePT.updateLights();
  }
  if (baked && fast) {
    await baked.load(c.date, c.time, kind);
    hideReference();
  }
  if (old?.userData?.temporary) old.dispose();
  if (kind === "overcast") tex.userData.temporary = true;
  drawMap();
  sunDirection();
}
function setMode(value) {
  if (value === "direct" && fast) {
    selectQuality(512)
      .then(() => setMode(value))
      .catch(showLightingError);
    return;
  }
  mode = value;
  $("appearance").setAttribute("aria-pressed", value === "appearance");
  $("direct").setAttribute("aria-pressed", value === "direct");
  pt.bounces = value === "direct" ? 1 : 20;
  for (const m of meshes) {
    if (m.material.name.startsWith("Glazing")) continue;
    m.material.color.copy(
      value === "direct"
        ? new T.Color(0.65, 0.65, 0.65)
        : m.userData.originalColor,
    );
    m.material.roughness = value === "direct" ? 1 : m.userData.roughness;
    m.material.map = value === "direct" ? null : m.userData.originalMap;
  }
  pt.updateMaterials();
  updateLighting();
  $("mode-label").textContent =
    value === "direct"
      ? "DIRECT SUN ONLY · NO SKY OR BOUNCES"
      : fast
        ? "PRECOMPUTED DAYLIGHT"
        : "PATH-TRACED DAYLIGHT";
  if (value === "direct" && sky === "overcast")
    toast("Overcast has no direct beam. Use Appearance for diffuse daylight.");
}
function addPlaces() {
  const sel = $("places");
  for (let l = 0; l < 2; l++) {
    const group = document.createElement("optgroup");
    group.label = l ? "Second floor" : "Main floor";
    fNow(l).rooms.forEach((r) => {
      const p = { name: r.name, x: r.label[0], y: r.label[1], level: l };
      const i = places.push(p) - 1;
      group.append(new Option(r.name, "" + i));
    });
    sel.append(group);
  }
  const g = document.createElement("optgroup");
  g.label = "Garden & grounds";
  data.outdoor.zones.slice(1).forEach((z, i) => {
    const pos = i === 4 ? [3.5, 20] : z.label.map((n) => n * F);
    const p = {
      name:
        i === 4 ? "Left side path" : z.name.replace(" (inferred edges)", ""),
      x: pos[0],
      y: pos[1],
      level: 0,
    };
    const idx = places.push(p) - 1;
    g.append(new Option(p.name, "" + idx));
  });
  sel.append(g);
  sel.value = "1";
  sel.onchange = () => {
    const p = places[+sel.value];
    siteMap = +sel.value >= 14;
    teleport(p.x, p.y, p.level, true);
  };
}
function drawMap() {
  if (!data) return;
  const svg = $("map"),
    f = fNow(),
    poly = siteMap ? meters(data.outdoor.parcel) : f.outline,
    xs = poly.map((p) => p[0]),
    ys = poly.map((p) => p[1]);
  const minX = Math.min(...xs) - 0.7,
    maxX = Math.max(...xs) + 0.7,
    minY = Math.min(...ys) - 0.7,
    maxY = Math.max(...ys) + 0.7;
  const sc = Math.min(275 / (maxX - minX), 225 / (maxY - minY)),
    cx = (minX + maxX) / 2,
    cy = (minY + maxY) / 2;
  const X = (x) => 150 + (x - cx) * sc,
    Y = (y) => 140 - (y - cy) * sc;
  mapTransform = { sc, cx, cy };
  let html = "";
  const shape = (p, fill, stroke = "#526b75") =>
    `<polygon points="${p.map((q) => X(q[0]) + "," + Y(q[1])).join(" ")}" fill="${fill}" stroke="${stroke}" stroke-width="1"/>`;
  if (siteMap) {
    html += shape(poly, "#253f38");
    for (let i = 1; i < data.outdoor.zones.length; i++)
      html += shape(
        meters(data.outdoor.zones[i].poly),
        i === 2 || i === 7 ? "#304d3d" : "#34454d",
      );
    html += shape(meters(data.outdoor.zones[0].poly), "#1f6476");
    html += shape(f.outline, "#1a282f");
    for (const idx of [1, 2, 7, 8]) {
      const z = data.outdoor.zones[idx],
        p = z.label.map((n) => n * F);
      html += `<text x="${X(p[0])}" y="${Y(p[1])}" text-anchor="middle">${z.short}</text>`;
    }
  } else {
    html += shape(f.outline, "#25343d");
    for (const r of f.rooms) {
      html += shape(
        r.poly,
        inside([player.x, player.y], r.poly) ? "#415b61" : "#25343d",
      );
      const words = r.name
        .replace("Kitchen / breakfast", "Kitchen")
        .replace("Stairs / landing", "Landing")
        .replace("Stairs / hall", "Hall")
        .split(" ");
      html += `<text text-anchor="middle" x="${X(r.label[0])}" y="${Y(r.label[1])}">${words.map((w, i) => `<tspan x="${X(r.label[0])}" dy="${i ? 12 : 0}">${w}</tspan>`).join("")}</text>`;
    }
    for (const w of f.walls) {
      html += `<path d="M${X(w.a[0])} ${Y(w.a[1])}L${X(w.b[0])} ${Y(w.b[1])}" stroke="#97aeb9" stroke-width="2"/>`;
      for (const h of w.holes)
        html += `<path d="M${X(h.a[0])} ${Y(h.a[1])}L${X(h.b[0])} ${Y(h.b[1])}" stroke="${h.window ? "#53b9d4" : "#25343d"}" stroke-width="3"/>`;
    }
  }
  const px = X(player.x),
    py = Y(player.y),
    nx = data.indoor.ux[1],
    ny = data.indoor.uy[1];
  html += `<path d="M270 30l${nx * 15} ${-ny * 15}" stroke="#b3c6cf" stroke-width="2"/><text x="${270 + nx * 21}" y="${30 - ny * 21}" text-anchor="middle">N</text><path d="M${px} ${py}l${Math.sin(yaw) * 19} ${-Math.cos(yaw) * 19}" stroke="#ffce7a" stroke-width="3"/><circle cx="${px}" cy="${py}" r="5" fill="#ffce7a" stroke="#17262e" stroke-width="2"/><text x="150" y="263" text-anchor="middle">${siteMap ? "Cleveland Avenue · front" : "Front of house ↓"}</text>`;
  svg.innerHTML = html;
  $("map-title").textContent = siteMap
    ? "Property"
    : level
      ? "Second floor"
      : "Main floor";
  $("map-scope").textContent = siteMap ? "Floor plan ↙" : "Site map ↗";
}
function mapTap(e) {
  const r = $("map").getBoundingClientRect(),
    sx = ((e.clientX - r.left) * 300) / r.width,
    sy = ((e.clientY - r.top) * 270) / r.height,
    { sc, cx, cy } = mapTransform,
    x = (sx - 150) / sc + cx,
    y = (140 - sy) / sc + cy;
  const l = siteMap ? 0 : level;
  const room = fNow(l).rooms.find((r) => inside([x, y], r.poly));
  teleport(x, y, l, !!room);
}
function viewTap(e) {
  const rect = canvas.getBoundingClientRect();
  pointer.set(
    ((e.clientX - rect.left) / rect.width) * 2 - 1,
    1 - ((e.clientY - rect.top) / rect.height) * 2,
  );
  ray.setFromCamera(pointer, camera);
  const hits = ray.intersectObjects(meshes, false);
  const hit = hits.find(
    (h) =>
      !h.object.material.name.startsWith("Glazing") &&
      !h.object.userData.tree &&
      !h.object.userData.detail,
  );
  if (!hit || !hit.object.userData.walkable) {
    toast("Tap a visible floor or clear ground.");
    return;
  }
  const x = hit.point.x,
    y = -hit.point.z,
    z = hit.point.y,
    l = z > 3 ? 1 : 0;
  if (teleport(x, y, l)) {
    $("destination").style.left = e.clientX - rect.left + "px";
    $("destination").style.top = e.clientY - rect.top + "px";
    $("destination").hidden = false;
    setTimeout(() => ($("destination").hidden = true), 650);
  }
}
function hidePanel(hidden) {
  document.body.classList.toggle("controls-hidden", hidden);
  $("panel-toggle").setAttribute("aria-expanded", !hidden);
  setTimeout(resize, 0);
}
function resize() {
  if (!renderer) return;
  const w = canvas.clientWidth,
    h = canvas.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  pt?.updateCamera();
}
function pruneTree(t) {
  if (!t.visible) return;
  if (!t.userData.privateGeometry) {
    t.geometry = t.geometry.clone();
    t.userData.privateGeometry = true;
  }
  t.updateWorldMatrix(true, false);
  const g = t.geometry,
    pos = g.attributes.position,
    idx = t.userData.baseIndex,
    valid = new Uint8Array(pos.count),
    p = new T.Vector3();
  for (let i = 0; i < pos.count; i++) {
    p.fromBufferAttribute(pos, i).applyMatrix4(t.matrixWorld);
    const x = p.x,
      y = -p.z,
      z = p.y;
    const blocked =
      (z < 8.5 && x > 3.9 && x < 17.6 && y > 13.2 && y < 22.55) ||
      (z < 7.4 &&
        data.indoor.floors.some((f) =>
          [
            [0, 0],
            [0.2, 0],
            [-0.2, 0],
            [0, 0.2],
            [0, -0.2],
          ].some(([dx, dy]) => inside([x + dx, y + dy], f.outline)),
        ));
    valid[i] = blocked ? 0 : 1;
  }
  const result = [];
  for (let i = 0; i < idx.length; i += 3)
    if (valid[idx[i]] && valid[idx[i + 1]] && valid[idx[i + 2]])
      result.push(idx[i], idx[i + 1], idx[i + 2]);
  g.setIndex(result);
}
function scaleTreeCrowns(s) {
  for (const t of trees) {
    t.visible = s !== 0;
    if (!s) continue;
    const c = t.userData.tree_center,
      C = new T.Vector3(c[0], c[2], -c[1]);
    const world = new T.Matrix4()
      .makeTranslation(C.x, C.y, C.z)
      .multiply(new T.Matrix4().makeScale(s, s, s))
      .multiply(new T.Matrix4().makeTranslation(-C.x, -C.y, -C.z))
      .multiply(t.userData.originalWorldMatrix);
    t.matrix.copy(t.parent.matrixWorld).invert().multiply(world);
    t.matrix.decompose(t.position, t.quaternion, t.scale);
  }
  canopyScale = s;
  scene.updateMatrixWorld(true);
}
function setupInput() {
  $("panel-toggle").onclick = () =>
    hidePanel(!document.body.classList.contains("controls-hidden"));
  $("map-scope").onclick = () => {
    siteMap = !siteMap;
    drawMap();
  };
  $("map").addEventListener("pointerup", mapTap);
  $("main-floor").onclick = () => switchFloor(0);
  $("second-floor").onclick = () => switchFloor(1);
  $("walk").onclick = () => setView("walk");
  $("orbit").onclick = () => setView("orbit");
  $("date").onchange = () => {
    if ($("date").value) updateLighting();
  };
  $("time").oninput = () => {
    $("clock").textContent = solar(
      $("date").value,
      +$("time").value,
      data.indoor,
    ).clock;
  };
  $("time").onchange = updateLighting;
  for (const b of document.querySelectorAll("[data-date]"))
    b.onclick = () => {
      $("date").value = $("date").value.slice(0, 4) + "-" + b.dataset.date;
      updateLighting();
    };
  for (const s of ["clear", "overcast"])
    $(s).onclick = () => {
      sky = s;
      for (const n of ["clear", "overcast"])
        $(n).setAttribute("aria-pressed", s === n);
      updateLighting();
    };
  $("appearance").onclick = () => setMode("appearance");
  $("direct").onclick = () => setMode("direct");
  $("quality").onchange = () =>
    selectQuality(+$("quality").value).catch(showLightingError);
  $("exposure").onchange = () => {
    hideReference();
    renderer.toneMappingExposure = +$("exposure").value;
    pt.reset();
    $("exposure-badge").textContent =
      `FIXED ${Math.log2(+$("exposure").value) > 0 ? "+" : ""}${Math.log2(+$("exposure").value)} EV`;
  };
  $("glazing").onchange = () => {
    hideReference();
    const trans = +$("glazing").value;
    for (const m of glasses)
      m.material.color.setScalar(Math.sqrt(trans / (0.96 * 0.96)));
    pt.updateMaterials();
    pt.reset();
  };
  $("canopy").onchange = () => {
    hideReference();
    scaleTreeCrowns(+$("canopy").value);
    for (const t of trees) pruneTree(t);
    pt.setScene(scene, camera);
    toast("Tree crowns updated. Daylight is recalculating.");
  };
  canvas.addEventListener("pointerdown", (e) => {
    if (!ready) return;
    hideReference();
    drag = {
      x: e.clientX,
      y: e.clientY,
      lastX: e.clientX,
      lastY: e.clientY,
      moved: false,
      id: e.pointerId,
    };
    canvas.setPointerCapture(e.pointerId);
    canvas.focus();
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!drag || drag.id !== e.pointerId) return;
    const dx = e.clientX - drag.lastX,
      dy = e.clientY - drag.lastY;
    if (Math.hypot(e.clientX - drag.x, e.clientY - drag.y) > 7)
      drag.moved = true;
    drag.lastX = e.clientX;
    drag.lastY = e.clientY;
    if (view === "walk" && drag.moved) {
      yaw -= dx * 0.004;
      pitch = Math.max(-1.4, Math.min(1.4, pitch - dy * 0.004));
      pose();
    }
  });
  canvas.addEventListener("pointerup", (e) => {
    if (drag && !drag.moved) viewTap(e);
    drag = null;
  });
  canvas.addEventListener("pointercancel", () => {
    drag = null;
    keys.clear();
  });
  canvas.addEventListener(
    "wheel",
    (e) => {
      if (view === "walk") {
        camera.fov = Math.max(35, Math.min(85, camera.fov + e.deltaY * 0.035));
        camera.updateProjectionMatrix();
        pt.updateCamera();
      }
    },
    { passive: true },
  );
  const keymap = {
    KeyW: "forward",
    ArrowUp: "forward",
    KeyS: "back",
    ArrowDown: "back",
    KeyA: "left",
    ArrowLeft: "left",
    KeyD: "right",
    ArrowRight: "right",
  };
  window.addEventListener("keydown", (e) => {
    if (/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    if (keymap[e.code]) {
      e.preventDefault();
      keys.add(keymap[e.code]);
    }
  });
  window.addEventListener("keyup", (e) => keys.delete(keymap[e.code]));
  window.addEventListener("blur", () => {
    keys.clear();
    drag = null;
  });
  for (const b of document.querySelectorAll("[data-move]")) {
    b.onpointerdown = (e) => {
      e.preventDefault();
      b.setPointerCapture(e.pointerId);
      keys.add(b.dataset.move);
    };
    b.onpointerup = b.onpointercancel = () => keys.delete(b.dataset.move);
    b.onclick = () => walkStep(b.dataset.move);
  }
  $("capture").onclick = () => {
    if (!fast && pt.samples < 128) {
      toast("Let this view reach 128 samples before saving a comparison.");
      return;
    }
    $("compare-img").src = canvas.toDataURL("image/png");
    $("compare-caption").textContent =
      `${$("location").textContent} · ${$("date").value} ${ss.clock} · ${sky} · glass ${Math.round(+$("glazing").value * 100)}% · trees ${canopyScale ? Math.round(canopyScale * 100) + "%" : "leaf off"} · ${$("exposure-badge").textContent} · ${Math.floor(pt.samples)} samples`;
    $("comparison").hidden = false;
  };
  $("close-compare").onclick = () => ($("comparison").hidden = true);
  $("reference").onclick = () => $("refs").showModal();
  $("close-refs").onclick = () => $("refs").close();
  const refs = [
    ["study-clear", "Study · clear", 0, 14.55, 19.5, 0, -0.09],
    ["study-overcast", "Study · overcast", 0, 14.55, 19.5, 0, -0.09],
    ["sunroom-clear", "Sunroom · clear", 1, 5.7, 23.3, 0, -0.09],
    ["yard-clear", "Garden · clear", 0, 10.8, 34, Math.PI, -0.06],
    ["pool-clear", "Pool · clear", 0, 10.6, 35.9, -2.1, -0.35],
    ["bath-clear", "Hall bath · clear", 1, 14.2, 20.8, Math.PI / 2, -0.09],
  ];
  $("ref-grid").innerHTML = refs
    .map(
      (r, i) =>
        `<article><img src="/references-v2/${r[0]}.png" alt="Cycles reference: ${r[1]}" loading="lazy"><p>${r[1]} · September 22, 1 PM EDT · +3 EV</p><button data-ref="${i}">Match this view</button></article>`,
    )
    .join("");
  for (const b of document.querySelectorAll("[data-ref]"))
    b.onclick = () => {
      const r = refs[+b.dataset.ref];
      siteMap = ["yard-clear", "pool-clear"].includes(r[0]);
      $("date").value = "2026-09-22";
      $("time").value = "780";
      $(r[0].includes("overcast") ? "overcast" : "clear").click();
      $("exposure").value = "8";
      $("exposure").onchange();
      $("canopy").value = "1";
      if (!fast) $("canopy").onchange();
      $("glazing").value = "0.82";
      if (!fast) $("glazing").onchange();
      setMode("appearance");
      yaw = r[5];
      pitch = r[6];
      camera.fov = 60;
      camera.updateProjectionMatrix();
      teleport(r[3], r[4], r[2], true);
      $("refs").close();
    };
  new ResizeObserver(resize).observe($("workspace"));
}
function walkStep(direction) {
  hideReference();
  const a =
      yaw +
      ({ forward: 0, back: Math.PI, left: -Math.PI / 2, right: Math.PI / 2 }[
        direction
      ] || 0),
    x = player.x + Math.sin(a) * 0.14,
    y = player.y + Math.cos(a) * 0.14;
  if (safe(x, y)) {
    player.x = x;
    player.y = y;
    pose();
  }
}
function hideReference() {
  const el = $("reference-preview");
  if (el) el.hidden = true;
}
function frame(t) {
  requestAnimationFrame(frame);
  if (!ready) return;
  const dt = Math.min(0.05, (t - last) / 1000 || 0.016);
  last = t;
  if (view === "walk" && keys.size) {
    hideReference();
    let f = (keys.has("forward") ? 1 : 0) - (keys.has("back") ? 1 : 0),
      r = (keys.has("right") ? 1 : 0) - (keys.has("left") ? 1 : 0),
      len = Math.hypot(f, r) || 1;
    const dx = ((Math.sin(yaw) * f + Math.cos(yaw) * r) * dt * 2) / len,
      dy = ((Math.cos(yaw) * f - Math.sin(yaw) * r) * dt * 2) / len;
    if (safe(player.x + dx, player.y)) player.x += dx;
    if (safe(player.x, player.y + dy)) player.y += dy;
    pose();
  }
  if (view === "orbit") orbit.update();
  if (fast) {
    if (baked.ready && (dirty || baked.changed)) {
      baked.render(camera);
      dirty = false;
      baked.changed = false;
      revision++;
      renderFrames++;
    }
    hideReference();
  } else if (pt.samples < quality) {
    pt.renderSample();
    revision++;
    renderFrames++;
  }
  if (pt.samples >= 128) hideReference();
  if (t - fpsStart > 1000) {
    fps = (renderFrames * 1000) / (t - fpsStart);
    renderFrames = 0;
    fpsStart = t;
  }
  if (t - lastHud > 500) {
    lastHud = t;
    const n = Math.floor(pt.samples);
    $("render-state").textContent = fast
      ? `Baked daylight · ${fps > 1 ? Math.round(fps) + " fps" : "ready"} · free walking`
      : `${n} samples · ${n >= quality ? "sample limit reached" : n < 32 ? "settling" : n < 128 ? "refining" : "converging"} · ${mode === "appearance" ? "20 bounces" : "direct only"}`;
  }
}
async function init() {
  try {
    [data, blocks, skyCases] = await Promise.all([
      fetch("/model-realism.json").then((r) => r.json()),
      fetch("/collision-realism.json").then((r) => r.json()),
      fetch("/skies/manifest.json").then((r) => r.json()),
    ]);
    navigation = new Navigation(data, blocks);
    renderer = new T.WebGLRenderer({
      canvas,
      antialias: true,
      preserveDrawingBuffer: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.3));
    renderer.toneMapping = T.AgXToneMapping;
    renderer.toneMappingExposure = 8;
    scene = new T.Scene();
    camera = new T.PerspectiveCamera(60, 1, 0.04, 400);
    orbit = new OrbitControls(camera, canvas);
    orbit.enabled = false;
    orbit.enableDamping = false;
    orbit.minDistance = 1;
    orbit.maxDistance = 90;
    orbit.maxPolarAngle = Math.PI * 0.48;
    orbit.addEventListener("change", () => {
      if (view === "orbit") {
        pt?.updateCamera();
        const dir = camera.getWorldDirection(new T.Vector3());
        yaw = Math.atan2(dir.x, -dir.z);
        drawMap();
        sunDirection();
      }
    });
    const gltf = await loadScene();
    house = gltf.scene;
    scene.add(house);
    const materialCopies = new Map();
    house.traverse((o) => {
      if (!o.isMesh) return;
      for (
        let parent = o.parent;
        parent && parent !== house;
        parent = parent.parent
      ) {
        for (const key of [
          "tree",
          "evergreen",
          "tree_center",
          "detail",
          "lightmap_group",
          "reflection_region",
          "walkable",
          "spring_only",
        ])
          if (
            o.userData[key] === undefined &&
            parent.userData[key] !== undefined
          )
            o.userData[key] = parent.userData[key];
      }
      meshes.push(o);
      const mk =
        o.material.uuid +
        ":" +
        (o.userData.lightmap_group || "detail") +
        ":" +
        (o.userData.reflection_region || "");
      if (!materialCopies.has(mk)) materialCopies.set(mk, o.material.clone());
      o.material = materialCopies.get(mk);
      o.material.side = T.DoubleSide;
      o.userData.originalColor = o.material.color.clone();
      o.userData.roughness = o.material.roughness;
      o.userData.originalMap = o.material.map;
      if (o.material.name.startsWith("Glazing")) {
        glasses.push(o);
        o.material.opacity = 1;
        o.material.transparent = false;
        o.material.transmission = 1;
        o.material.ior = 1.5;
        o.material.thickness = 0.005;
        o.material.attenuationDistance = Infinity;
        o.material.color.setScalar(Math.sqrt(0.82 / (0.96 * 0.96)));
        o.material.roughness = 0.012;
      }
      if (o.material.name === "Pool water") {
        o.material.thickness = 0.69;
        o.material.attenuationDistance = 3;
        o.material.attenuationColor = new T.Color(0.75, 0.94, 0.96);
      }
      if (o.userData.tree) {
        trees.push(o);
        o.userData.baseIndex =
          o.geometry.index?.array ||
          Uint32Array.from(
            { length: o.geometry.attributes.position.count },
            (_, i) => i,
          );
        o.userData.originalScale = o.scale.clone();
        o.userData.originalPosition = o.position.clone();
      }
    });
    scene.updateMatrixWorld(true);
    for (const t of trees)
      t.userData.originalWorldMatrix = t.matrixWorld.clone();
    sun = new T.DirectionalLight(new T.Color(1, 0.91, 0.76), 3);
    scene.add(sun, sun.target);
    await updateLighting();
    baked = new BakedLighting(renderer, scene, meshes);
    await baked.init();
    pt = stubTracer;
    await baked.load($("date").value, +$("time").value, sky);
    $("glazing").disabled = $("canopy").disabled = true;
    resize();
    pose();
    if (!fast) pt.setScene(scene, camera);
    addPlaces();
    setupInput();
    ready = true;
    $("loading").hidden = true;
    $("reference-preview").hidden = fast;
    if (innerWidth < 761) hidePanel(true);
    drawMap();
    requestAnimationFrame(frame);
    window.study = {
      get state() {
        return {
          ready,
          player: { ...player },
          level,
          view,
          mode,
          sky,
          solar: ss,
          samples: fast ? baked.entry?.samples || 0 : pt.samples,
          baked: fast,
          bakedReady: !!baked?.ready,
          fps,
          frameRevision: revision,
          scenario: baked?.entry?.key,
          exposure: renderer.toneMappingExposure,
          canopyScale,
          camera: camera.position.toArray(),
        };
      },
      safe,
      teleport,
      setMode,
      setView,
      updateLighting,
      pose,
      get pt() {
        return pt;
      },
      scene,
      camera,
      renderer,
      data,
    };
  } catch (e) {
    console.error(e);
    $("loading-detail").textContent =
      `Unable to start the 3D renderer: ${e.message}. A browser with WebGL 2 is required.`;
  }
}
function showLightingError(e) {
  console.error(e);
  $("loading-detail").textContent = e.message;
  toast(e.message);
}
function setupLiveTracer() {
  pt = new WebGLPathTracer(renderer);
  pt.bounces = 20;
  pt.transmissiveBounces = 24;
  pt.filterGlossyFactor = 0.15;
  pt.renderScale = innerWidth < 761 ? 0.8 : 0.45;
  pt.tiles.set(2, 2);
  pt.renderDelay = 50;
  pt.fadeDuration = 150;
  pt.minSamples = 1;
  pt.dynamicLowRes = true;
  pt.lowResScale = 0.2;
  pt.rasterizeScene = false;
  const denoise = new DenoiseMaterial({ sigma: 3, kSigma: 1, threshold: 0.2 });
  const denoiseQuad = new FullScreenQuad(denoise);
  pt.renderToCanvasCallback = (target, r, quad) => {
    if (pt.samples < 4) {
      quad.render(r);
      return;
    }
    denoise.map = target.texture;
    denoise.opacity = 1;
    denoiseQuad.render(r);
  };

  livePT = pt;
  pt.setScene(scene, camera);
  return pt;
}
async function selectQuality(value) {
  $("quality").value = String(value);
  hideReference();
  quality = value;
  fast = value === 0;
  if (fast) {
    mode = "appearance";
    $("appearance").setAttribute("aria-pressed", "true");
    $("direct").setAttribute("aria-pressed", "false");
    if (+$("glazing").value !== 0.82 || +$("canopy").value !== 1) {
      $("glazing").value = "0.82";
      for (const g of glasses)
        g.material.color.setScalar(Math.sqrt(0.82 / (0.96 * 0.96)));
      $("canopy").value = "1";
      scaleTreeCrowns(1);
      for (const t of trees)
        if (t.userData.privateGeometry)
          t.geometry.setIndex(new T.BufferAttribute(t.userData.baseIndex, 1));
    }
    for (const m of meshes) {
      if (m.material.name.startsWith("Glazing")) continue;
      m.material.color.copy(m.userData.originalColor);
      m.material.roughness = m.userData.roughness;
      m.material.map = m.userData.originalMap;
      m.material.needsUpdate = true;
    }
    pt = stubTracer;
    dirty = true;
    await updateLighting();
  } else {
    pt = livePT || setupLiveTracer();
    pt.renderScale = value === 2048 ? 1 : 0.75;
    pt.updateCamera();
    pt.reset();
  }
  $("glazing").disabled = $("canopy").disabled = fast;
  $("mode-label").textContent = fast
    ? "PRECOMPUTED DAYLIGHT"
    : "LIVE PATH-TRACED DAYLIGHT";
}
const stubTracer = {
  samples: 0,
  renderScale: 1,
  updateCamera() {
    dirty = true;
  },
  reset() {
    dirty = true;
  },
  updateMaterials() {
    dirty = true;
  },
  setScene() {
    dirty = true;
  },
  updateEnvironment() {
    dirty = true;
  },
  updateLights() {
    dirty = true;
  },
};

init();
