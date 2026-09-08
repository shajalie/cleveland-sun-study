import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import { createReadStream } from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { createInterface } from "node:readline";

/** A private child process renders stationary views; moving views stay responsive. */
export class CyclesRenderer {
  constructor(root) {
    this.root = root;
    this.directory = path.join(root, ".runtime", "cycles-cache");
    this.phase = "starting";
    this.error = "";
    this.cache = new Map();
    this.pending = null;
    this.active = null;
    this.child = null;
  }

  async start() {
    this.phase = "starting";
    const candidates = [
      process.env.DAYLIGHT_BLENDER,
      path.join(this.root, "runtime", "blender", "blender.exe"),
      path.resolve(
        this.root,
        "../../tools/blender-4.5.13-windows-x64/blender.exe",
      ),
      "C:/Program Files/Blender Foundation/Blender 4.5/blender.exe",
    ].filter(Boolean);
    let executable;
    for (const candidate of candidates) {
      try {
        await fs.access(candidate);
        executable = candidate;
        break;
      } catch {}
    }
    if (!executable) {
      this.phase = "unavailable";
      this.error = "Blender rendering runtime is not installed";
      return;
    }
    const sceneDigest = createHash("sha256");
    for await (const chunk of createReadStream(
      path.join(this.root, "cleveland-realism.blend"),
    ))
      sceneDigest.update(chunk);
    this.sceneHash = sceneDigest.digest("hex");
    const renderingCode = await Promise.all(
      ["remote/cycles_worker.py", "scripts/rendering.py"].map((file) =>
        fs.readFile(path.join(this.root, file)),
      ),
    );
    this.pipelineHash = createHash("sha256")
      .update(Buffer.concat(renderingCode))
      .digest("hex");
    this.sceneVersion = this.sceneHash + ":" + this.pipelineHash;
    this.presets = [];
    try {
      const manifest = JSON.parse(
        await fs.readFile(
          path.join(this.root, "public/native-presets/manifest.json"),
          "utf8",
        ),
      );
      if (
        manifest.sceneSha256 === this.sceneHash &&
        manifest.pipelineSha256 === this.pipelineHash
      )
        this.presets = manifest.views;
    } catch {}
    await fs.mkdir(this.directory, { recursive: true });
    if (this.phase === "closed") return;
    this.child = spawn(
      executable,
      [
        "--background",
        "--python-exit-code",
        "1",
        "--python",
        path.join(this.root, "remote", "cycles_worker.py"),
      ],
      {
        cwd: this.root,
        windowsHide: true,
        stdio: ["pipe", "pipe", "pipe"],
        env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1" },
      },
    );
    const lines = createInterface({ input: this.child.stdout });
    const child = this.child;
    lines.on("line", (line) => {
      if (child !== this.child) return;
      if (!line.startsWith("CYCLES_EVENT ")) return;
      try {
        this.receive(JSON.parse(line.slice(13)), child).catch((error) => {
          if (child === this.child) this.fail(error);
        });
      } catch (error) {
        this.fail(error);
      }
    });
    this.child.stderr.on("data", () => {});
    this.child.on("error", (error) => {
      if (child === this.child) this.fail(error);
    });
    this.child.on("exit", (code) => {
      if (child === this.child && this.phase !== "closed")
        this.fail(Error(`Blender worker exited (${code})`));
    });
  }

  fail(error) {
    this.error = error.message;
    this.phase = "error";
    this.active = null;
  }

  async receive(message, child) {
    if (message.type === "ready") {
      this.phase = "ready";
      this.gpu = message.gpu;
      this.dispatch();
    } else if (message.type === "rendered") {
      if (!/^[a-f0-9]{64}$/.test(message.key))
        throw Error("Invalid worker result");
      const frame = await fs.readFile(
        path.join(this.directory, message.key + ".jpg"),
      );
      if (child !== this.child) return;
      this.cache.set(message.key, {
        frame,
        seconds: message.seconds,
        samples: message.samples,
      });
      while (this.cache.size > 32)
        this.cache.delete(this.cache.keys().next().value);
      this.active = null;
      this.phase = "ready";
      this.dispatch();
      this.trimDiskCache().catch(() => {});
    } else if (message.type === "error") {
      this.active = null;
      this.error = message.message;
      this.phase = "ready";
      this.pending = null;
    }
  }

  key(view) {
    return createHash("sha256")
      .update(JSON.stringify([this.sceneVersion, view]))
      .digest("hex");
  }

  async trimDiskCache() {
    // Only files created by this worker are eligible; retain the newest 200 views.
    const names = (await fs.readdir(this.directory)).filter((name) =>
      /^[a-f0-9]{64}(?:\.pending)?\.jpg$/.test(name),
    );
    const entries = await Promise.all(
      names.map(async (name) => {
        const file = path.join(this.directory, name);
        return { file, name, modified: (await fs.stat(file)).mtimeMs };
      }),
    );
    const complete = entries
      .filter((entry) => !entry.name.includes(".pending."))
      .sort((a, b) => b.modified - a.modified);
    const stale = entries.filter(
      (entry) =>
        entry.name.includes(".pending.") &&
        Date.now() - entry.modified > 3600000,
    );
    await Promise.all(
      [...complete.slice(200), ...stale].map((entry) =>
        fs.unlink(entry.file).catch(() => {}),
      ),
    );
  }

  async request(view) {
    if (
      !this.sceneVersion ||
      ["error", "unavailable", "closed"].includes(this.phase)
    )
      return null;
    const key = this.key(view);
    if (this.cache.has(key)) return this.cache.get(key);
    const signature = (v) =>
      JSON.stringify([
        v.position,
        v.direction,
        v.fov,
        v.exposure,
        v.date,
        v.time,
        v.sky,
      ]);
    const preset = this.presets?.find(
      (p) => signature(p.view) === signature(view),
    );
    if (preset && /^[a-z-]+\.jpg$/.test(preset.file)) {
      const frame = await fs.readFile(
        path.join(this.root, "public/native-presets", preset.file),
      );
      if (createHash("sha256").update(frame).digest("hex") === preset.sha256) {
        const hit = { frame, cached: true, precomputed: true, samples: 128 };
        this.cache.set(key, hit);
        return hit;
      }
    }
    if (this.active?.key === key || this.pending?.key === key) return null;
    try {
      const frame = await fs.readFile(path.join(this.directory, key + ".jpg"));
      const hit = { frame, cached: true, samples: 128 };
      this.cache.set(key, hit);
      return hit;
    } catch {}
    this.pending = { key, view };
    if (this.phase === "idle") this.start().catch((error) => this.fail(error));
    this.dispatch();
    return null;
  }

  dispatch() {
    if (this.phase !== "ready" || this.active || !this.pending) return;
    if (this.cache.has(this.pending.key)) {
      this.pending = null;
      return;
    }
    this.active = this.pending;
    this.pending = null;
    this.phase = "rendering";
    this.child.stdin.write(JSON.stringify(this.active) + "\n");
  }

  cancelPending() {
    this.pending = null;
    if (this.active) {
      // Stop only this owned render worker so GPU time immediately returns to walking.
      const child = this.child;
      this.child = null;
      this.active = null;
      this.phase = "idle";
      child?.kill();
    }
  }
  status() {
    return {
      phase: this.phase,
      error: this.error,
      gpu: this.gpu || [],
      samples: 128,
    };
  }
  close() {
    this.phase = "closed";
    this.pending = null;
    this.child?.stdin.end();
    this.child?.kill();
  }
}
