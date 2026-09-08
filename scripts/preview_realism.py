"""Render inspection views of the rebuilt scene with matching fixed sky/exposure."""

import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "scripts"))
from rendering import configure_glass, configure_sky

args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
bpy.ops.wm.open_mainfile(filepath=str(P / "cleveland-realism.blend"))
configure_glass()
s = bpy.context.scene
s.use_nodes = False
s.render.engine = "CYCLES"
s.cycles.samples = 128
s.cycles.use_denoising = True
s.cycles.device = "GPU"
s.cycles.adaptive_threshold = 0.04
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type == "OPTIX"
s.render.resolution_x = 1000
s.render.resolution_y = 700
s.render.resolution_percentage = 100
s.render.image_settings.file_format = "PNG"
s.view_settings.view_transform = "AgX"
s.view_settings.look = "AgX - Medium High Contrast"
s.view_settings.exposure = (
    float(args[args.index("--exposure") + 1]) if "--exposure" in args else 3
)
c = next(
    c
    for c in json.loads((P / "public/skies/manifest.json").read_text())
    if c["date"] == "2026-09-22" and c["time"] == 780
)
configure_sky(s, c, "clear", P)
views = {
    "study": ((14.55, 19.5, 2.42), (14.55, 24.5, 1.969)),
    "living": ((14.55, 19.5, 2.42), (14.65, 15.0, 1.9)),
    "garden": ((9.8, 36.3, 1.636), (10.7, 22.5, 3.9)),
    "front": ((9, 0, 1.62), (11.5, 14, 3.7)),
    "wall-detail": ((13.4, 17.8, 2.15), (11.915, 17, 2)),
    "leather-detail": ((14.55, 19.5, 2.42), (16.1, 18.5, 1.5)),
    "roof-detail": ((12, 9, 10), (12, 16, 7.6)),
    "steps-detail": ((11, 8.5, 1.4), (10.6, 9.7, 0.4)),
}
cam = s.camera
cam.data.type = "PERSP"
cam.data.lens = 28
for name, (p, target) in views.items():
    if args and name not in args:
        continue
    cam.data.lens = 22 if name == "garden" else 28
    if name.endswith("-detail"):
        cam.data.lens = 45
    cam.location = p
    cam.rotation_euler = (
        (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    )
    s.render.filepath = str(P / "evidence" / ("realism-" + name + ".png"))
    bpy.ops.render.render(write_still=True)
    print("PREVIEW_READY", name, flush=True)
