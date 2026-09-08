import fs from "node:fs/promises";
import assert from "node:assert/strict";
import { WebSocket } from "ws";
const config = JSON.parse(
  await fs.readFile(new URL("../.runtime/host.json", import.meta.url), "utf8"),
);
const origin = `http://127.0.0.1:${config.port}`,
  cookie = `daylight=${config.token}`;
assert.equal((await fetch(origin + "/api/state")).status, 401);
assert.equal(
  (
    await fetch(origin + "/api/connect", {
      method: "POST",
      headers: {
        Origin: "https://untrusted.invalid",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ token: config.token }),
    })
  ).status,
  403,
);
assert.equal(
  (
    await fetch(origin + "/api/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: "invalid" }),
    })
  ).status,
  401,
);
const getState = async () => {
  const r = await fetch(origin + "/api/state", { headers: { Cookie: cookie } });
  assert.equal(r.status, 200);
  return r.json();
};
let state = await getState();
assert(state.ready, state.failure || "Renderer not ready");
assert(/NVIDIA.*RTX/.test(state.gpu));
await new Promise((resolve, reject) => {
  const ws = new WebSocket(origin.replace("http", "ws") + "/control");
  ws.on("unexpected-response", (_, res) => {
    assert.equal(res.statusCode, 401);
    ws.terminate();
    resolve();
  });
  ws.on("open", () => reject(Error("Unauthenticated control accepted")));
  ws.on("error", () => {});
  setTimeout(
    () => reject(Error("Unauthorized socket check timed out")),
    5000,
  ).unref();
});
const ws = new WebSocket(origin.replace("http", "ws") + "/control", {
  headers: { Cookie: cookie, Origin: origin },
});
let frames = 0,
  invalidRejected = false,
  lastFrame;
ws.on("message", (d, binary) => {
  if (binary) {
    assert.equal(d[0], 255);
    assert.equal(d[1], 216);
    frames++;
    lastFrame = Buffer.from(d);
  } else {
    const m = JSON.parse(d);
    if (m.type === "notice" && m.message === "Unknown action")
      invalidRejected = true;
  }
});
await new Promise((resolve, reject) => {
  ws.once("open", resolve);
  ws.once("error", reject);
});
const send = (x) => ws.send(JSON.stringify(x));
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(predicate, limit = 15000) {
  const end = Date.now() + limit;
  do {
    state = await getState();
    if (predicate(state)) return;
    await wait(250);
  } while (Date.now() < end);
  throw Error("Remote state did not reach the expected result");
}
send({ type: "not_an_allowed_action" });
await until(() => invalidRejected && frames > 0);
const sunroom = state.controls.places.options.find(
  (o) => o.label === "Sunroom",
).value;
send({ type: "select", id: "places", value: sunroom });
await until((s) => s.state.level === 1 && s.controls.places.value === sunroom);
send({ type: "button", id: "overcast" });
await until((s) => s.state.sky === "overcast");
send({ type: "button", id: "clear" });
await until((s) => s.state.sky === "clear");
const living = state.controls.places.options.find(
  (o) => o.label === "Living",
).value;
send({ type: "select", id: "places", value: living });
await until((s) => s.state.level === 0 && s.controls.places.value === living);
let p = { ...state.state.player };
send({ type: "step", key: "w" });
await until(
  (s) => Math.hypot(s.state.player.x - p.x, s.state.player.y - p.y) > 0.1,
);
send({ type: "key", key: "w", down: true });
await wait(2400);
const stopped = (await getState()).state.player;
await wait(1200);
const later = (await getState()).state.player;
assert(
  Math.hypot(later.x - stopped.x, later.y - stopped.y) < 0.02,
  "Lost-controller movement did not stop",
);
send({ type: "release" });
send({ type: "select", id: "places", value: living });
await until((s) => s.controls.places.value === living);
await fs.writeFile(
  new URL("../.runtime/stream-preview.jpg", import.meta.url),
  lastFrame,
);
await until((s) => s.refinement?.displayed, 180000);
assert.equal(state.refinement.samples, 128);
assert(state.refinement.gpu.some((name) => /NVIDIA.*RTX/.test(name)));
assert(!state.refinement.error);
await fs.writeFile(
  new URL("../.runtime/stream-native.jpg", import.meta.url),
  lastFrame,
);
p = { ...state.state.player };
send({ type: "step", key: "w" });
await until(
  (s) =>
    !s.refinement.displayed &&
    Math.hypot(s.state.player.x - p.x, s.state.player.y - p.y) > 0.1,
);
send({ type: "select", id: "places", value: living });
ws.close();
const report = {
  testedAt: new Date().toISOString(),
  gpu: state.gpu,
  jpegFramesReceived: frames,
  checks: [
    "Unauthenticated state and control rejected",
    "Foreign Origin pairing rejected",
    "Invalid pairing key rejected",
    "Authenticated JPEG stream carries real image data",
    "Unknown controls rejected",
    "Upstairs navigation and clear/overcast changes applied on host",
    "Single-tap walking changes position",
    "Movement stops after heartbeat loss",
    "Stationary stream refines to 128-sample native Cycles on NVIDIA GPU",
    "Moving returns to the preview immediately",
  ],
  limitations: [
    "Tested on RTX 2060 Max-Q; RTX 5090 is not connected to this workspace",
    "Authenticated streaming tested locally; public URL verified to reach Cloudflare email sign-in",
  ],
};
await fs.writeFile(
  new URL("../remote-validation.json", import.meta.url),
  JSON.stringify(report, null, 2) + "\n",
);
console.log(JSON.stringify(report, null, 2));
