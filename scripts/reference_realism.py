"""Cycles reference views of the actual v2 scene, independent of the lightmaps."""

import bpy, json, math, sys, hashlib
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "scripts"))
from rendering import configure_glass, configure_sky

bpy.ops.wm.open_mainfile(filepath=str(P / "cleveland-realism.blend"))
configure_glass()
s = bpy.context.scene
s.use_nodes = False
s.render.engine = "CYCLES"
s.cycles.samples = 128
s.cycles.use_denoising = True
s.cycles.device = "GPU"
s.cycles.adaptive_threshold = 0.015
s.cycles.max_bounces = 20
s.cycles.diffuse_bounces = 12
s.cycles.transmission_bounces = 16
s.cycles.transparent_max_bounces = 32
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type == "OPTIX"
s.render.resolution_x = 960
s.render.resolution_y = 720
s.render.resolution_percentage = 100
s.render.image_settings.file_format = "PNG"
s.view_settings.view_transform = "AgX"
s.view_settings.look = "AgX - Medium High Contrast"
s.view_settings.exposure = 3
cam = s.camera
cam.data.type = "PERSP"
cam.data.sensor_fit = "VERTICAL"
cam.data.sensor_height = 24
cam.data.lens = 24 / (2 * math.tan(math.radians(60) / 2))
case = next(
    c
    for c in json.loads((P / "public/skies/manifest.json").read_text())
    if c["date"] == "2026-09-22" and c["time"] == 780
)
for o in s.objects:
    if o.get("spring_only"):
        o.hide_render = True
out = P / "public/references-v2"
out.mkdir(exist_ok=True)
presets = P / "public/native-presets"
presets.mkdir(exist_ok=True)
records = []
views = [
    ("study-clear", "clear", (14.55, 19.5, 2.42), 0, -0.09),
    ("study-overcast", "overcast", (14.55, 19.5, 2.42), 0, -0.09),
    ("sunroom-clear", "clear", (5.7, 23.3, 5.57), 0, -0.09),
    ("yard-clear", "clear", (10.8, 34, 1.636), math.pi, -0.06),
    ("pool-clear", "clear", (10.6, 35.9, 1.636), -2.1, -0.35),
    ("bath-clear", "clear", (14.2, 20.8, 5.57), math.pi / 2, -0.09),
]
for name, kind, pos, yaw, pitch in views:
    configure_sky(s, case, kind, P)
    cam.location = pos
    cam.rotation_euler = (
        Vector(
            (
                math.sin(yaw) * math.cos(pitch),
                math.cos(yaw) * math.cos(pitch),
                math.sin(pitch),
            )
        )
        .to_track_quat("-Z", "Y")
        .to_euler()
    )
    s.render.filepath = str(out / (name + ".png"))
    s.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    s.render.image_settings.file_format = "JPEG"
    s.render.image_settings.quality = 94
    image_path = presets / (name + ".jpg")
    bpy.data.images["Render Result"].save_render(filepath=str(image_path), scene=s)
    direction = (
        math.sin(yaw) * math.cos(pitch),
        math.sin(pitch),
        -math.cos(yaw) * math.cos(pitch),
    )
    records.append(
        {
            "file": image_path.name,
            "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
            "view": {
                "position": [round(pos[0], 4), round(pos[2], 4), round(-pos[1], 4)],
                "direction": [round(v, 4) for v in direction],
                "fov": 60,
                "exposure": 8,
                "date": case["date"],
                "time": case["time"],
                "sky": kind,
            },
        }
    )
    print("REFERENCE_READY", name, flush=True)
manifest = {
    "sceneSha256": hashlib.sha256(
        (P / "cleveland-realism.blend").read_bytes()
    ).hexdigest(),
    "pipelineSha256": hashlib.sha256(
        (P / "remote/cycles_worker.py").read_bytes()
        + (P / "scripts/rendering.py").read_bytes()
    ).hexdigest(),
    "samples": 128,
    "views": records,
}
(presets / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
