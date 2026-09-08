import http from "node:http";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { randomBytes, timingSafeEqual } from "node:crypto";
import puppeteer from "puppeteer-core";
import { WebSocketServer, WebSocket } from "ws";
import QRCode from "qrcode";
import { execFile } from "node:child_process";
import { SharingManager } from "./sharing.mjs";
import { createAccessVerifier } from "./sharing-auth.mjs";
import { CyclesRenderer } from "./cycles-renderer.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const runtime = path.join(root, ".runtime");
const cycles = new CyclesRenderer(root);
let detailedView = false;
await fs.mkdir(runtime, { recursive: true });
const port = Number(process.env.DAYLIGHT_PORT || 5182),
  renderPort = Number(process.env.DAYLIGHT_RENDER_PORT || 5181);
const stateFile = path.join(runtime, "host.json");
let saved = {};
try {
  saved = JSON.parse(await fs.readFile(stateFile, "utf8"));
} catch {}
const token = saved.token || randomBytes(24).toString("base64url");
let browser,
  page,
  gpu = "",
  ready = false,
  failure = "",
  lastStatus = {},
  closing = false;
let connectionJob = { busy: false, error: "" };
const localDashboard = (req) =>
  !req.websiteConnection &&
  ["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(req.socket.remoteAddress) &&
  ["127.0.0.1", "localhost", "[::1]"].includes(
    new URL("http://" + req.headers.host).hostname,
  );
const clients = new Set(),
  keys = new Set();
let lastInput = 0,
  commandQueue = Promise.resolve(),
  statusBusy = false;
const streamStats = { frames: 0, bytes: 0, lastFrameAt: null };
const mime = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".glb": "model/gltf-binary",
  ".hdr": "application/octet-stream",
};
const equal = (a, b) =>
  typeof a === "string" &&
  a.length === b.length &&
  timingSafeEqual(Buffer.from(a), Buffer.from(b));
const cookie = (req) =>
  (req.headers.cookie || "")
    .split(";")
    .map((x) => x.trim())
    .find((x) => x.startsWith("daylight="))
    ?.slice(9);
const authorized = (req) =>
  !!req.websiteIdentity ||
  (!req.websiteConnection && equal(cookie(req), token));
const originOK = (req) =>
  !req.headers.origin ||
  (() => {
    try {
      return new URL(req.headers.origin).host === req.headers.host;
    } catch {
      return false;
    }
  })();
function json(res, code, value) {
  res.writeHead(code, {
    "Content-Type": "application/json",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  });
  res.end(JSON.stringify(value));
}
async function body(req) {
  let text = "";
  for await (const chunk of req) {
    text += chunk;
    if (text.length > 16384) throw Error("Request too large");
  }
  return JSON.parse(text || "{}");
}
async function staticFile(res, base, relative) {
  try {
    const file = path.resolve(base, relative);
    if (!file.startsWith(base + path.sep))
      return json(res, 403, { error: "Forbidden" });
    const bytes = await fs.readFile(file);
    res.writeHead(200, {
      "Content-Type": mime[path.extname(file)] || "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
      "Cache-Control": "no-cache",
    });
    res.end(bytes);
  } catch {
    json(res, 404, { error: "Not found" });
  }
}
const sceneServer = http.createServer((req, res) => {
  const u = new URL(req.url, "http://localhost");
  staticFile(
    res,
    path.join(root, "dist"),
    u.pathname === "/" ? "index.html" : decodeURIComponent(u.pathname).slice(1),
  );
});
await new Promise((resolve, reject) =>
  sceneServer.once("error", reject).listen(renderPort, "127.0.0.1", resolve),
);
const sharingPort = Number(process.env.DAYLIGHT_SHARING_PORT || 5184);
const sharing = await new SharingManager(root, {
  originPort: sharingPort,
  onChange: () => {
    for (const ws of clients)
      if (
        ws.identity &&
        (!sharing.config.enabled ||
          !sharing.config.emails.includes(ws.identity.email))
      )
        ws.close(1008, "Access removed");
  },
}).init();
const verifyWebsite = createAccessVerifier(() => sharing.config);
const attempts = new Map();
const handleRequest = async (req, res) => {
  try {
    const u = new URL(req.url, "http://localhost");
    res.setHeader("Referrer-Policy", "no-referrer");
    res.setHeader("X-Frame-Options", "DENY");
    if (u.pathname === "/health")
      return json(res, 200, {
        service: "cleveland-daylight-host",
        pid: process.pid,
        ready,
      });
    if (u.pathname === "/api/sharing-qr") {
      if (!authorized(req) || !localDashboard(req) || !sharing.config.enabled)
        return json(res, 403, { error: "Sharing unavailable" });
      const bytes = await QRCode.toBuffer(
        "https://" + sharing.config.hostname + "/",
        { width: 260, margin: 2 },
      );
      res.writeHead(200, {
        "Content-Type": "image/png",
        "Cache-Control": "no-store",
      });
      return res.end(bytes);
    }
    if (u.pathname === "/api/sharing") {
      if (!authorized(req) || !localDashboard(req) || !originOK(req))
        return json(res, 403, {
          error: "Website sharing is managed only from the local PC dashboard.",
        });
      if (req.method === "GET") return json(res, 200, sharing.status());
      if (req.method !== "POST")
        return json(res, 405, { error: "Method not allowed" });
      const b = await body(req);
      if (!["enable", "disable", "emails"].includes(b.action))
        return json(res, 400, { error: "Invalid sharing action" });
      sharing.run(() =>
        b.action === "enable"
          ? sharing.configure(b)
          : b.action === "disable"
            ? sharing.disable()
            : sharing.updateEmails(b.emails),
      );
      return json(res, 202, { busy: true });
    }
    if (u.pathname === "/api/connect" && req.method === "POST") {
      if (req.websiteConnection)
        return json(res, 403, {
          error: "Sign in with an approved email through the website.",
        });
      if (!originOK(req)) return json(res, 403, { error: "Origin denied" });
      const ip = req.socket.remoteAddress,
        attempt = attempts.get(ip) || { count: 0, since: Date.now() };
      if (Date.now() - attempt.since > 60000) {
        attempt.count = 0;
        attempt.since = Date.now();
      }
      if (attempt.count >= 12)
        return json(res, 429, { error: "Try again in a minute" });
      const b = await body(req);
      if (!equal(b.token, token)) {
        attempt.count++;
        attempts.set(ip, attempt);
        return json(res, 401, { error: "Incorrect pairing key" });
      }
      attempts.delete(ip);
      res.setHeader(
        "Set-Cookie",
        `daylight=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000`,
      );
      return json(res, 200, { ok: true });
    }
    if (u.pathname === "/api/state")
      return authorized(req)
        ? json(res, 200, {
            ready,
            gpu,
            failure,
            stream: streamStats,
            refinement: { ...cycles.status(), displayed: detailedView },
            ...lastStatus,
          })
        : json(res, 401, { error: "Pair this browser" });
    if (u.pathname === "/api/tailscale" && req.method === "POST") {
      if (!authorized(req))
        return json(res, 401, { error: "Pair this browser" });
      if (!originOK(req) || !localDashboard(req))
        return json(res, 403, {
          error:
            "Change connection settings from the local PC dashboard, including through Moonlight.",
        });
      const b = await body(req);
      if (typeof b.enabled !== "boolean")
        return json(res, 400, { error: "Choose enabled or disabled" });
      if (connectionJob.busy)
        return json(res, 409, { error: "Connection setup is already running" });
      connectionJob = { busy: true, error: "" };
      execFile(
        "powershell.exe",
        [
          "-NoProfile",
          "-ExecutionPolicy",
          "Bypass",
          "-File",
          path.join(root, "remote/configure-tailscale.ps1"),
          "-Action",
          b.enabled ? "enable" : "disable",
        ],
        { windowsHide: true, timeout: 60000, maxBuffer: 16384 },
        (error, stdout, stderr) => {
          connectionJob = {
            busy: false,
            error: error
              ? stdout.trim() ||
                "Tailscale setup failed. Check the Windows Tailscale app and try again."
              : "",
          };
        },
      );
      return json(res, 202, { busy: true });
    }
    if (u.pathname === "/api/connection") {
      if (req.websiteIdentity)
        return json(res, 200, {
          url: "https://" + sharing.config.hostname + "/",
          websiteUrl: "https://" + sharing.config.hostname + "/",
          private: false,
          canConfigure: false,
          job: { busy: false, error: "" },
        });
      if (!authorized(req))
        return json(res, 401, { error: "Pair this browser" });
      let config = {};
      try {
        config = JSON.parse(
          (
            await fs.readFile(path.join(runtime, "connection.json"), "utf8")
          ).replace(/^\uFEFF/, ""),
        );
      } catch {}
      const url = config.phone_url ? config.phone_url + "#" + token : null;
      const websiteUrl = url
        ? "https://cleveland-sun-study.sammyhajalie2g.chatgpt.site/#host=" +
          encodeURIComponent(url)
        : null;
      return json(res, 200, {
        url,
        websiteUrl,
        private: !!url,
        canConfigure: localDashboard(req),
        job: connectionJob,
        qr: url
          ? await QRCode.toDataURL(websiteUrl, { width: 300, margin: 2 })
          : null,
      });
    }
    if (
      u.pathname === "/methods" ||
      u.pathname === "/validation-results.json" ||
      u.pathname === "/geometry-audit.html" ||
      u.pathname === "/reference-sources.json" ||
      u.pathname.startsWith("/references/") ||
      u.pathname.startsWith("/references-v2/")
    ) {
      if (!authorized(req))
        return json(res, 401, { error: "Pair this browser" });
      return staticFile(
        res,
        path.join(root, "dist"),
        u.pathname === "/methods"
          ? "validation.html"
          : decodeURIComponent(u.pathname).slice(1),
      );
    }
    const files = {
      "/": "client.html",
      "/client.js": "client.js",
      "/style.css": "style.css",
      "/sharing-ui.js": "sharing-ui.js",
    };
    if (files[u.pathname])
      return staticFile(res, path.join(root, "remote"), files[u.pathname]);
    json(res, 404, { error: "Not found" });
  } catch (e) {
    json(res, 400, { error: e.message });
  }
};
const server = http.createServer(handleRequest);
const websiteServer = http.createServer(async (req, res) => {
  req.websiteConnection = true;
  try {
    req.websiteIdentity = await verifyWebsite(req);
  } catch {
    return json(res, 403, {
      error: "Website sharing is off or this email is not authorized.",
    });
  }
  return handleRequest(req, res);
});
await new Promise((resolve, reject) =>
  websiteServer.once("error", reject).listen(sharingPort, "127.0.0.1", resolve),
);
const wss = new WebSocketServer({ noServer: true, maxPayload: 4096 });
const upgrade = (req, socket, head) => {
  if (req.url !== "/control" || !authorized(req) || !originOK(req)) {
    socket.end("HTTP/1.1 401 Unauthorized\r\nConnection: close\r\n\r\n");
    return;
  }
  wss.handleUpgrade(req, socket, head, (ws) => wss.emit("connection", ws, req));
};
server.on("upgrade", upgrade);
websiteServer.on("upgrade", async (req, socket, head) => {
  req.websiteConnection = true;
  try {
    req.websiteIdentity = await verifyWebsite(req);
  } catch {
    socket.end("HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n");
    return;
  }
  upgrade(req, socket, head);
});
function send(ws, obj) {
  if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}
async function releaseKeys() {
  for (const k of keys) await page?.keyboard.up(k).catch(() => {});
  keys.clear();
}
const selectIds = new Set([
  "date",
  "time",
  "places",
  "quality",
  "exposure",
  "canopy",
  "glazing",
]);
const buttons = new Set([
  "appearance",
  "clear",
  "overcast",
  "main-floor",
  "second-floor",
  "walk",
  "orbit",
  "map-scope",
]);
async function action(a) {
  if (!ready || !page) throw Error(failure || "GPU renderer is starting");
  if (a.type === "select") {
    if (!selectIds.has(a.id) || typeof a.value !== "string")
      throw Error("Invalid control");
    if (a.id === "quality" && a.value !== "0")
      throw Error("The stream uses automatic Blender refinement");
    await page.evaluate(({ id, value }) => {
      const e = document.getElementById(id);
      if (e.disabled) throw Error("This setting requires live rays");
      if (![...e.options].some((o) => o.value === value))
        throw Error("Invalid option");
      e.value = value;
      e.dispatchEvent(new Event("change", { bubbles: true }));
      if (id === "quality" && value === "512") {
        window.study.pt.renderScale = 0.75;
        window.study.pt.reset();
      }
    }, a);
  } else if (a.type === "button") {
    if (!buttons.has(a.id)) throw Error("Invalid button");
    await page.evaluate((id) => document.getElementById(id).click(), a.id);
  } else if (a.type === "pointer") {
    if (
      !["down", "up", "move"].includes(a.phase) ||
      !Number.isFinite(a.x) ||
      !Number.isFinite(a.y)
    )
      throw Error("Invalid pointer");
    const vp = page.viewport(),
      x = Math.max(0, Math.min(1, a.x)) * vp.width,
      y = Math.max(0, Math.min(1, a.y)) * vp.height;
    await page.mouse.move(x, y);
    if (a.phase === "down") await page.mouse.down();
    if (a.phase === "up") await page.mouse.up();
    lastInput = Date.now();
  } else if (a.type === "key") {
    if (!["w", "a", "s", "d"].includes(a.key) || typeof a.down !== "boolean")
      throw Error("Invalid movement");
    if (a.down) {
      keys.add(a.key);
      await page.keyboard.down(a.key);
    } else {
      keys.delete(a.key);
      await page.keyboard.up(a.key);
    }
    lastInput = Date.now();
  } else if (a.type === "step") {
    const direction = { w: "forward", a: "left", s: "back", d: "right" }[a.key];
    if (!direction) throw Error("Invalid step");
    await page.evaluate(
      (d) => document.querySelector('[data-move="' + d + '"]').click(),
      direction,
    );
  } else if (a.type === "heartbeat") {
    lastInput = Date.now();
  } else if (a.type === "release") {
    await releaseKeys();
    await page.mouse.up();
  } else if (a.type === "map") {
    if (
      !Number.isFinite(a.x) ||
      !Number.isFinite(a.y) ||
      a.x < 0 ||
      a.x > 1 ||
      a.y < 0 ||
      a.y > 1
    )
      throw Error("Invalid map point");
    await page.evaluate(({ x, y }) => {
      const e = document.getElementById("map"),
        r = e.getBoundingClientRect();
      e.dispatchEvent(
        new PointerEvent("pointerup", {
          clientX: r.left + x * r.width,
          clientY: r.top + y * r.height,
          bubbles: true,
        }),
      );
    }, a);
  } else if (a.type === "zoom") {
    if (!Number.isFinite(a.delta)) throw Error("Invalid zoom");
    await page.mouse.wheel({ deltaY: Math.max(-300, Math.min(300, a.delta)) });
  } else throw Error("Unknown action");
}
wss.on("connection", (ws, req) => {
  ws.identity = req.websiteIdentity;
  clients.add(ws);
  send(ws, {
    type: "status",
    ready,
    gpu,
    failure,
    stream: streamStats,
    refinement: { ...cycles.status(), displayed: detailedView },
    ...lastStatus,
  });
  ws.on("message", (raw, binary) => {
    if (binary) return ws.close(1003);
    let a;
    try {
      a = JSON.parse(raw);
    } catch {
      return ws.close(1007);
    }
    commandQueue = commandQueue
      .then(() => {
        if (
          ws.identity &&
          (!sharing.config.enabled ||
            !sharing.config.emails.includes(ws.identity.email) ||
            ws.identity.expires <= Date.now() / 1000)
        )
          throw Error("Access removed");
        return action(a);
      })
      .catch((e) => send(ws, { type: "notice", message: e.message }));
  });
  ws.on("close", () => {
    clients.delete(ws);
    if (!clients.size) cycles.cancelPending();
    releaseKeys();
    page?.mouse.up().catch(() => {});
  });
});
await new Promise((resolve, reject) =>
  server
    .once("error", reject)
    .listen(port, process.env.DAYLIGHT_BIND || "127.0.0.1", resolve),
);
await fs.writeFile(
  stateFile,
  JSON.stringify(
    {
      token,
      pid: process.pid,
      port,
      renderPort,
      started: new Date().toISOString(),
    },
    null,
    2,
  ),
);
console.log(`HOST_LISTENING http://127.0.0.1:${port}/`);
async function startRenderer() {
  try {
    const candidates = [
      ...new Set(
        [
          process.env.DAYLIGHT_BROWSER,
          "C:/Program Files/Google/Chrome/Application/chrome.exe",
          "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
          process.env.LOCALAPPDATA &&
            path.join(
              process.env.LOCALAPPDATA,
              "Google/Chrome/Application/chrome.exe",
            ),
        ].filter(Boolean),
      ),
    ];
    const launchErrors = [];
    for (const executablePath of candidates) {
      try {
        await fs.access(executablePath);
      } catch {
        continue;
      }
      try {
        browser = await puppeteer.launch({
          executablePath,
          headless: true,
          pipe: true,
          userDataDir: path.join(runtime, "chrome-render-profile"),
          defaultViewport: { width: 960, height: 720, deviceScaleFactor: 1 },
          args: [
            "--enable-gpu",
            "--force-high-performance-gpu",
            "--use-angle=d3d11",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
          ],
          timeout: 60000,
        });
        console.log("BROWSER_STARTED " + executablePath);
        break;
      } catch (e) {
        launchErrors.push(path.basename(executablePath) + ": " + e.message);
        console.warn("BROWSER_RETRY " + path.basename(executablePath));
      }
    }
    if (!browser)
      throw Error(
        "No render browser could start. Install or update Google Chrome, then rerun START-DAYLIGHT.cmd. " +
          launchErrors.join("; "),
      );
    page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${renderPort}/render.html`, {
      waitUntil: "domcontentloaded",
    });
    await page.waitForFunction(() => window.study?.state.ready, {
      timeout: 120000,
    });
    gpu = await page.evaluate(() => {
      const gl = window.study.renderer.getContext(),
        e = gl.getExtension("WEBGL_debug_renderer_info");
      return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : "Unknown GPU";
    });
    if (!/NVIDIA.*(?:RTX|GeForce|Quadro)/i.test(gpu))
      throw Error(
        `Dedicated NVIDIA GPU was not selected: ${gpu}. Set the render browser to High performance in Windows Graphics settings and restart the launcher.`,
      );
    await page.addStyleTag({
      content:
        "header,.view-top,.view-bottom,#pad,#reference-preview,#comparison,#toast{display:none!important}main{height:100vh!important}aside{position:fixed!important;display:block!important;left:-2000px!important;top:0!important;width:326px!important;height:900px!important}#workspace{width:100vw!important;height:100vh!important}",
    });
    await page.evaluate(() => {
      window.study.pt.renderScale = 0.75;
      window.study.pt.reset();
    });
    ready = true;
    cycles.start().catch((error) => cycles.fail(error));
    console.log("GPU_VERIFIED " + gpu);
  } catch (e) {
    failure = e.message;
    console.error("HOST_ERROR " + failure);
  }
}
startRenderer();
setInterval(() => {
  for (const ws of clients)
    if (
      ws.identity &&
      (!sharing.config.enabled ||
        !sharing.config.emails.includes(ws.identity.email) ||
        ws.identity.expires <= Date.now() / 1000)
    )
      ws.close(1008, "Sign in again");
}, 1000).unref();
sharing.resume().catch((e) => {
  sharing.job.error = e.message;
});
setInterval(async () => {
  if (!page || !ready || statusBusy) return;
  statusBusy = true;
  if (keys.size && Date.now() - lastInput > 1500) await releaseKeys();
  try {
    lastStatus = await page.evaluate(() => ({
      state: window.study.state,
      toast: document.getElementById("toast").hidden
        ? ""
        : document.getElementById("toast").textContent,
      map: document.getElementById("map").outerHTML,
      mapTitle: document.getElementById("map-title").textContent,
      controls: Object.fromEntries(
        [
          "date",
          "time",
          "places",
          "quality",
          "exposure",
          "canopy",
          "glazing",
        ].map((id) => {
          const e = document.getElementById(id);
          return [
            id,
            {
              value: e.value,
              disabled: e.disabled,
              options: [...e.options].map((o) => ({
                value: o.value,
                label: o.textContent,
              })),
            },
          ];
        }),
      ),
      pressed: Object.fromEntries(
        [
          "appearance",
          "direct",
          "clear",
          "overcast",
          "main-floor",
          "second-floor",
          "walk",
          "orbit",
        ].map((id) => [
          id,
          document.getElementById(id).getAttribute("aria-pressed") === "true",
        ]),
      ),
    }));
    // The streamed host uses native Cycles for detail; browser tracing can stall
    // while constructing a very large BVH and is reserved for standalone use.
    lastStatus.controls.quality.options = [
      { value: "0", label: "Automatic · Blender detail when still" },
    ];
    for (const ws of clients)
      send(ws, {
        type: "status",
        ready,
        gpu,
        failure,
        refinement: { ...cycles.status(), displayed: detailedView },
        ...lastStatus,
      });
  } catch (e) {
    failure = e.message;
  } finally {
    statusBusy = false;
  }
}, 1000).unref();
async function frames() {
  let lastRevision = -1,
    lastCapture = 0,
    stableSince = Date.now(),
    currentRayView = null,
    shownRayKey = null;
  while (!closing) {
    const started = Date.now();
    if (ready && clients.size) {
      try {
        const revision = await page.evaluate(
          () => window.study.state.frameRevision,
        );
        if (revision !== lastRevision) {
          stableSince = started;
          currentRayView = null;
          shownRayKey = null;
          detailedView = false;
          cycles.cancelPending();
        }
        let detailed = null;
        if (started - stableSince > 1200 && !keys.size) {
          if (!currentRayView)
            currentRayView = await page.evaluate(() => {
              const study = window.study,
                camera = study.camera;
              const direction = camera.getWorldDirection(
                camera.position.clone(),
              );
              const round = (n) => Math.round(n * 10000) / 10000;
              return {
                position: camera.position.toArray().map(round),
                direction: direction.toArray().map(round),
                fov: camera.fov,
                exposure: study.renderer.toneMappingExposure,
                date: document.getElementById("date").value,
                time: +document.getElementById("time").value,
                sky: study.state.sky,
              };
            });
          detailed = await cycles.request(currentRayView);
        }
        const rayKey = detailed && cycles.key(currentRayView);
        if (
          revision !== lastRevision ||
          started - lastCapture > 1500 ||
          (rayKey && rayKey !== shownRayKey)
        ) {
          const frame =
            detailed?.frame ||
            (await page.screenshot({
              type: "jpeg",
              quality: 78,
              encoding: "binary",
            }));
          lastRevision = revision;
          shownRayKey = rayKey;
          detailedView = !!detailed;
          lastCapture = Date.now();
          streamStats.frames++;
          streamStats.bytes = frame.length;
          streamStats.lastFrameAt = new Date().toISOString();
          for (const ws of clients)
            if (ws.readyState === WebSocket.OPEN && ws.bufferedAmount < 350000)
              ws.send(frame, { binary: true });
        }
      } catch (e) {
        failure = e.message;
      }
    }
    await new Promise((r) =>
      setTimeout(r, Math.max(10, 50 - (Date.now() - started))),
    );
  }
}
frames();
async function close() {
  if (closing) return;
  closing = true;
  await releaseKeys();
  for (const ws of clients) ws.close();
  await browser?.close();
  cycles.close();
  await sharing.stopProcess();
  server.close();
  websiteServer.close();
  sceneServer.close();
  process.exit(0);
}
process.on("SIGINT", close);
process.on("SIGTERM", close);
