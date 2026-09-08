import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { CyclesRenderer } from "../remote/cycles-renderer.mjs";

const renderer = new CyclesRenderer(path.resolve("."));
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
try {
  await renderer.start();
  const boot = Date.now();
  while (renderer.phase === "starting" && Date.now() - boot < 30000)
    await wait(100);
  assert.equal(renderer.phase, "ready", renderer.error);
  const bundled = await renderer.request({
    position: [14.55, 2.42, -19.5],
    direction: [0, -0.0899, -0.996],
    fov: 60,
    exposure: 8,
    date: "2026-09-22",
    time: 780,
    sky: "clear",
  });
  assert(
    bundled?.precomputed,
    "Default view should use the bundled Cycles render",
  );
  const view = {
    position: [14.55, 2.42, -19.5],
    direction: [0, -0.09, -0.995942],
    fov: 60,
    exposure: 8,
    date: "2026-09-22",
    time: 780,
    sky: "clear",
  };
  const start = Date.now();
  let result;
  while (Date.now() - start < 300000) {
    assert(!["error", "unavailable"].includes(renderer.phase), renderer.error);
    result = await renderer.request(view);
    if (result) break;
    await wait(1000);
  }
  assert(result, "Native Cycles view did not complete");
  const firstViewWallSeconds = (Date.now() - start) / 1000;
  assert.deepEqual([...result.frame.subarray(0, 2)], [255, 216]);
  assert.deepEqual([...result.frame.subarray(-2)], [255, 217]);
  assert.equal(result.samples, 128);
  assert(
    renderer.gpu.some((name) => /NVIDIA|RTX/.test(name)),
    "Dedicated GPU not verified",
  );
  const cached = await renderer.request(view);
  assert.strictEqual(
    cached,
    result,
    "Identical view should return the cached image",
  );
  const alternate = { ...view, fov: 61.123 };
  // An uncached request is killed as soon as walking resumes, then another view works.
  await fs.rm(path.join(renderer.directory, renderer.key(alternate) + ".jpg"), {
    force: true,
  });
  await renderer.request(alternate);
  assert.equal(renderer.phase, "rendering");
  const canceledPid = renderer.child.pid;
  renderer.cancelPending();
  assert.equal(renderer.phase, "idle");
  assert.equal(renderer.child, null);
  const restart = Date.now();
  let restarted;
  while (Date.now() - restart < 300000) {
    assert(!["error", "unavailable"].includes(renderer.phase), renderer.error);
    restarted = await renderer.request(alternate);
    if (restarted) break;
    await wait(500);
  }
  assert(restarted, "Canceled worker did not restart");
  assert.notEqual(renderer.child.pid, canceledPid);
  assert.strictEqual(
    await renderer.request(view),
    result,
    "Completed views survive cancellation",
  );
  const report = {
    testedAt: new Date().toISOString(),
    gpu: renderer.gpu,
    samples: result.samples,
    firstViewWallSeconds,
    renderSeconds: result.seconds,
    jpegBytes: result.frame.length,
    cacheReuse: true,
    bundledFirstView: true,
    cancellationAndRestart: true,
    transport: "private child stdin/stdout",
  };
  await fs.writeFile(
    "cycles-validation.json",
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(JSON.stringify(report, null, 2));
} finally {
  renderer.close();
}
