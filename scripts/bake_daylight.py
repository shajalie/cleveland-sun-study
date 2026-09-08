"""Cycles diffuse lightmaps for freely navigable, discrete daylight scenarios.

No camera is baked. Maps contain direct and indirect irradiance without albedo.
The viewer applies physical materials and multiplies Lambertian baked maps by pi.
"""

import bpy, bmesh, json, math, sys, time, numpy as np, struct, zlib, hashlib
from pathlib import Path

P = Path(__file__).resolve().parents[1]
OUT = P / "public/lightmaps"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(P / "scripts"))
from denoise_lightmap import LightmapDenoiser
from rendering import configure_glass, configure_sky

denoiser = LightmapDenoiser(bpy.app.binary_path)
args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
prepare = "--prepare" in args
test = "--test" in args
size = 512 if test else 2048
samples = 8 if test else 96
bpy.ops.wm.open_mainfile(
    filepath=str(P / ("cleveland-realism.blend" if prepare else "cleveland-bake.blend"))
)
s = bpy.context.scene
s.use_nodes = False
s.render.engine = "CYCLES"
s.cycles.samples = samples
s.cycles.max_bounces = 16
s.cycles.diffuse_bounces = 10
s.cycles.transmission_bounces = 12
s.cycles.transparent_max_bounces = 32
s.cycles.use_denoising = True
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type == "OPTIX"
s.cycles.device = "GPU"
groups = {k: [] for k in ["interior", "exterior"]}
# Merge detail twigs in scenes made by the initial upgrade pass.
twigs = [
    o
    for o in s.objects
    if o.type == "MESH" and (" twig" in o.name or " primary branch" in o.name)
]
if twigs:
    bpy.ops.object.select_all(action="DESELECT")
    for o in twigs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = twigs[0]
    bpy.ops.object.join()
    bpy.context.object.name = "Batched tree branches"
    bpy.context.object["detail"] = True
for o in s.objects:
    if (
        o.type != "MESH"
        or not o.data.materials
        or o.get("detail")
        or o.name.startswith(
            ("Context ground", "Neighbor", "Pool water", "Glass", "Validation")
        )
    ):
        continue
    if any(
        m and m.name.startswith(("Glazing", "Pool water")) for m in o.data.materials
    ):
        continue
    from mathutils import Vector

    center = o.matrix_world @ (sum((Vector(c) for c in o.bound_box), Vector()) / 8)
    group = (
        "interior"
        if 4 < center.x < 17.5
        and 13.4 < center.y < 26.7
        and not o.name.startswith(("Property ground", "Roof", "Hip roof"))
        else "exterior"
    )
    o["lightmap_group"] = group
    groups[group].append(o)
    if group == "interior":
        o["reflection_region"] = "upper" if center.z > 3.8 else "lower"
if prepare:
    for group, objects in groups.items():
        # Smart-project one combined world-space mesh, then copy UVs back by loop.
        # Multi-object smart_project does not guarantee a single non-overlapping atlas.
        verts = []
        faces = []
        loop_sources = []
        for o in objects:
            offset = len(verts)
            verts.extend(o.matrix_world @ v.co for v in o.data.vertices)
            for p in o.data.polygons:
                faces.append(tuple(offset + v for v in p.vertices))
                loop_sources.extend((o, li) for li in p.loop_indices)
            if "Lightmap" not in o.data.uv_layers:
                o.data.uv_layers.new(name="Lightmap")
        me = bpy.data.meshes.new("Temporary atlas")
        me.from_pydata(verts, [], faces)
        me.update()
        me.uv_layers.new(name="Lightmap")
        # Edit-mode conversion can reorder polygons/loops. Keep a stable corner ID.
        ids = me.attributes.new("_source_loop", "INT", "CORNER")
        ids.data.foreach_set("value", np.arange(len(loop_sources), dtype=np.int32))
        # Adjacent wall/arch strips are separate source objects. Weld their temporary
        # chart vertices so each continuous surface gets a continuous lighting island.
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.00001)
        bm.to_mesh(me)
        bm.free()
        atlas = bpy.data.objects.new("Temporary atlas", me)
        s.collection.objects.link(atlas)
        bpy.ops.object.select_all(action="DESELECT")
        atlas.select_set(True)
        bpy.context.view_layer.objects.active = atlas
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(
            angle_limit=math.radians(66),
            island_margin=0.004,
            area_weight=0,
            correct_aspect=True,
            scale_to_bounds=False,
        )
        bpy.ops.object.mode_set(mode="OBJECT")
        reordered = 0
        for li, corner in enumerate(me.attributes["_source_loop"].data):
            o, source_li = loop_sources[corner.value]
            o.data.uv_layers["Lightmap"].data[source_li].uv = (
                me.uv_layers["Lightmap"].data[li].uv
            )
            reordered += li != corner.value
        print("UV_CORNERS_REORDERED", group, reordered, flush=True)
        bpy.data.objects.remove(atlas, do_unlink=True)
        bpy.data.meshes.remove(me)
        print("UV_READY", group, len(objects), flush=True)
    # Tiny grass blades inherit the irradiance of the ground directly beneath them.
    # This preserves canopy shadows without allocating a separate island per blade.
    grass = bpy.data.objects.get("Individual lawn blades")
    if grass:
        values = np.empty(len(grass.data.vertices) * 3, np.float32)
        grass.data.vertices.foreach_get("co", values)
        xy = values.reshape(-1, 3)[:, :2]
        coords = np.zeros((len(xy), 2), np.float32)
        assigned = np.zeros(len(xy), bool)
        for ground in s.objects:
            if ground.type != "MESH" or not ground.name.startswith(
                ("Front lawn", "Rear lawn")
            ):
                continue
            ground.data.calc_loop_triangles()
            for tri in ground.data.loop_triangles:
                if tri.normal.z < 0.5:
                    continue
                pts = np.array(
                    [
                        (ground.matrix_world @ ground.data.vertices[i].co)[:2]
                        for i in tri.vertices
                    ]
                )
                a, b, c = pts
                den = np.cross(b - a, c - a)
                if abs(den) < 1e-10:
                    continue
                delta = xy - a
                v = (delta[:, 0] * (c - a)[1] - delta[:, 1] * (c - a)[0]) / den
                w = ((b - a)[0] * delta[:, 1] - (b - a)[1] * delta[:, 0]) / den
                mask = (v >= -0.001) & (w >= -0.001) & (v + w <= 1.001)
                uv = np.array(
                    [ground.data.uv_layers["Lightmap"].data[i].uv for i in tri.loops]
                )
                coords[mask] = (
                    uv[0]
                    + v[mask, None] * (uv[1] - uv[0])
                    + w[mask, None] * (uv[2] - uv[0])
                )
                assigned |= mask
        uv = grass.data.uv_layers.get("Lightmap") or grass.data.uv_layers.new(
            name="Lightmap"
        )
        indices = np.empty(len(grass.data.loops), np.int32)
        grass.data.loops.foreach_get("vertex_index", indices)
        uv.data.foreach_set("uv", coords[indices].ravel())
        grass["lightmap_group"] = "exterior"
        print("GRASS_LIGHT_TRANSFER", int(assigned.sum()), len(assigned), flush=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(P / "cleveland-bake.blend"))
    # Both UV sets exported; every source texture explicitly uses UVMap (set zero).
    bpy.ops.export_scene.gltf(
        filepath=str(P / ".runtime/house-baked-raw.glb"),
        export_format="GLB",
        export_extras=True,
        export_cameras=False,
        export_lights=False,
    )
    if "--prepare-only" in args:
        sys.exit(0)
scene_hash = hashlib.sha256((P / "cleveland-bake.blend").read_bytes()).hexdigest()
configure_glass()
# Bake each atlas as one mesh. Baking thousands of separate objects rebuilds
# the Cycles scene for every object and is needlessly expensive.
for group, objects in list(groups.items()):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = "Bake target " + group
    groups[group] = [o]
cases = json.loads((P / "public/skies/manifest.json").read_text())
if "--case" in args:
    key = args[args.index("--case") + 1]
    cases = [c for c in cases if c["date"] + "-" + str(c["time"]) == key]
elif test:
    cases = [next(c for c in cases if c["date"] == "2026-09-22" and c["time"] == 780)]
kind = "overcast" if "--overcast" in args else "clear"
reportfile = OUT / "manifest.json"
report = json.loads(reportfile.read_text()) if reportfile.exists() else []
for c in cases:
    key = c["date"] + "-" + str(c["time"]) + "-" + kind
    if (
        any(
            x["key"] == key
            and x["resolution"] >= size
            and x.get("sceneSha256") == scene_hash
            for x in report
        )
        and "--force" not in args
    ):
        continue
    started = time.monotonic()
    configure_sky(s, c, kind, P)
    for o in s.objects:
        if o.get("tree") and not o.get("evergreen", False):
            o.hide_render = c["date"].endswith(("12-21", "03-20"))
        # Azalea bloom is not assumed at the March equinox; the photos show a later season.
        if o.get("spring_only"):
            o.hide_render = True
    paths = {}
    ranges = {}
    for group, objects in groups.items():
        target = bpy.data.images.new(
            "Bake " + group, width=size, height=size, float_buffer=True
        )
        target.colorspace_settings.name = "Non-Color"
        for m in bpy.data.materials:
            if not m.use_nodes:
                continue
            for n in m.node_tree.nodes:
                n.select = False
            node = m.node_tree.nodes.get(
                "Daylight bake target"
            ) or m.node_tree.nodes.new("ShaderNodeTexImage")
            node.name = "Daylight bake target"
            node.image = target
            node.select = True
            m.node_tree.nodes.active = node
        bpy.ops.object.select_all(action="DESELECT")
        for o in objects:
            o.select_set(True)
            o.data.uv_layers.active = o.data.uv_layers["Lightmap"]
            o.data.uv_layers["Lightmap"].active_render = True
        bpy.context.view_layer.objects.active = objects[0]
        s.render.bake.use_pass_color = False
        s.render.bake.use_pass_direct = True
        s.render.bake.use_pass_indirect = True
        s.render.bake.margin = 2
        s.render.bake.use_clear = True
        print("BAKE_START", key, group, size, samples, flush=True)
        bpy.ops.object.bake(type="DIFFUSE", uv_layer="Lightmap")
        # Store lossless half-float linear radiance. Conversion to RGBM is done by the
        # packaging helper; float data is retained for numerical and render comparisons.
        px = np.asarray(target.pixels[:], np.float32).reshape(size, size, 4)
        rgb = denoiser.apply(np.maximum(0, px[:, :, :3]))
        maximum = float(rgb.max())
        dynamic_range = 2 ** math.ceil(math.log2(max(1, maximum)))
        multiplier = np.maximum(
            1 / 255, np.ceil(np.clip(rgb.max(axis=2) / dynamic_range, 0, 1) * 255) / 255
        )
        encoded = np.empty((size, size, 4), np.uint8)
        encoded[:, :, :3] = np.clip(
            np.rint(rgb / (multiplier[:, :, None] * dynamic_range) * 255), 0, 255
        ).astype(np.uint8)
        encoded[:, :, 3] = np.rint(multiplier * 255).astype(np.uint8)

        def chunk(kind, data):
            return (
                struct.pack(">I", len(data))
                + kind
                + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
            )

        rows = b"".join(b"\x00" + row.tobytes() for row in encoded[::-1])
        png = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">2I5B", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 6))
            + chunk(b"IEND", b"")
        )
        (OUT / (key + "-" + group + ".png")).write_bytes(png)
        paths[group] = "/lightmaps/" + key + "-" + group + ".png"
        ranges[group] = dynamic_range
        print(
            "BAKE_COMPLETE",
            group,
            "maximum",
            maximum,
            "RGBM_range",
            dynamic_range,
            "seconds",
            time.monotonic() - started,
            flush=True,
        )
        bpy.data.images.remove(target)
    # Local reflection probes keep the indoor glossy response from reflecting an
    # unobstructed sky. They are static approximations, not screen-space ray tracing.
    probes = {}
    cam = s.camera
    cam.data.type = "PANO"
    cam.data.panorama_type = "EQUIRECTANGULAR"
    cam.rotation_euler = Vector((1, 0, 0)).to_track_quat("-Z", "Y").to_euler()
    s.render.resolution_x = 512
    s.render.resolution_y = 256
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "HDR"
    s.view_settings.view_transform = "Raw"
    s.view_settings.look = "None"
    s.view_settings.exposure = 0
    s.cycles.samples = 32
    for region, pos in [("lower", (14.55, 18.5, 2.42)), ("upper", (5.7, 23.3, 5.57))]:
        cam.location = pos
        path = OUT / (key + "-" + region + "-reflection.hdr")
        s.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        probes[region] = "/lightmaps/" + path.name
    s.cycles.samples = samples
    entry = {
        "key": key,
        "date": c["date"],
        "time": c["time"],
        "sky": kind,
        "maps": paths,
        "ranges": ranges,
        "probes": probes,
        "encoding": "RGBM-linear",
        "resolution": size,
        "samples": samples,
        "seconds": time.monotonic() - started,
        "glazing": 0.82,
        "seasonalFoliage": True,
        "sceneSha256": scene_hash,
        "denoiser": "OIDN HDR",
    }
    report = [x for x in report if x["key"] != key] + [entry]
    reportfile.write_text(json.dumps(report, indent=2))
    print("SCENARIO_COMPLETE", key, entry["seconds"], flush=True)
