"""Private stdin/stdout worker: render camera views in actual Blender Cycles.

No network listener, arbitrary commands, filenames or scripts are accepted.
"""

import json
import math
import queue
import re
import sys
import threading
import time
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from rendering import configure_glass, configure_sky

CACHE = ROOT / ".runtime/cycles-cache"
CACHE.mkdir(parents=True, exist_ok=True)
jobs = queue.Queue()


def event(kind, **values):
    print("CYCLES_EVENT " + json.dumps({"type": kind, **values}), flush=True)


def receive():
    for line in sys.stdin:
        try:
            job = json.loads(line)
            if isinstance(job, dict):
                jobs.put(job)
        except ValueError:
            event("error", message="Invalid render request")
    jobs.put(None)


def render(scene, job, cases):
    key = job.get("key", "")
    if not re.fullmatch("[a-f0-9]{64}", key):
        raise ValueError("Invalid cache key")
    view = job["view"]
    case = next(
        c for c in cases if c["date"] == view["date"] and c["time"] == view["time"]
    )
    configure_sky(scene, case, view["sky"], ROOT)
    for obj in scene.objects:
        if obj.get("tree") and not obj.get("evergreen", False):
            obj.hide_render = view["date"].endswith(("12-21", "03-20"))
        if obj.get("spring_only"):
            obj.hide_render = True
    position = view["position"]
    direction = view["direction"]
    if (
        len(position) != 3
        or len(direction) != 3
        or not all(math.isfinite(v) for v in position + direction)
    ):
        raise ValueError("Invalid camera")
    camera = scene.camera
    camera.data.type = "PERSP"
    camera.data.sensor_fit = "VERTICAL"
    camera.data.sensor_height = 24
    camera.data.lens = 12 / math.tan(math.radians(max(20, min(110, view["fov"]))) / 2)
    camera.location = (position[0], -position[2], position[1])
    camera.rotation_euler = (
        Vector((direction[0], -direction[2], direction[1]))
        .to_track_quat("-Z", "Y")
        .to_euler()
    )
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.view_settings.exposure = math.log2(max(0.01, min(64, view["exposure"])))
    scene.render.filepath = str(CACHE / (key + ".pending.jpg"))
    started = time.monotonic()
    bpy.ops.render.render(write_still=True)
    (CACHE / (key + ".pending.jpg")).replace(CACHE / (key + ".jpg"))
    event(
        "rendered",
        key=key,
        seconds=time.monotonic() - started,
        samples=scene.cycles.samples,
    )


def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "cleveland-realism.blend"))
    configure_glass()
    scene = bpy.context.scene
    scene.use_nodes = False
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.cycles.adaptive_threshold = 0.015
    scene.cycles.max_bounces = 20
    scene.cycles.diffuse_bounces = 12
    scene.cycles.transmission_bounces = 16
    scene.cycles.transparent_max_bounces = 32
    scene.render.use_persistent_data = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 94
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == "OPTIX"
    gpu = [device.name for device in prefs.devices if device.use]
    if not gpu:
        raise RuntimeError("An OptiX-compatible NVIDIA GPU is required")
    cases = json.loads((ROOT / "public/skies/manifest.json").read_text())
    threading.Thread(target=receive, daemon=True).start()
    event("ready", gpu=gpu)
    while True:
        job = jobs.get()
        while not jobs.empty():
            job = jobs.get()
        if job is None:
            break
        try:
            render(scene, job, cases)
        except Exception as error:
            event("error", key=job.get("key"), message=str(error))


if __name__ == "__main__":
    main()
