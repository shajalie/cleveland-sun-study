"""Export stage of the reproducible scene build."""

import bpy, json


def build(*, D, OUT, P, RODS, collision, mesh, scene):
    # Batch twig geometry so detailed trees do not require thousands of draw calls.
    for material_name, (rv, rf) in RODS.items():
        mesh(
            "Batched tree branches " + material_name,
            rv,
            rf,
            bpy.data.materials[material_name],
            True,
        )
    twigs = [
        o
        for o in scene.objects
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
    # Correct texture UVs explicitly to prevent the new lightmap UVs changing surface maps.
    bpy.context.view_layer.update()
    print("DETAIL_GEOMETRY_READY", len(scene.objects), flush=True)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for o in list(scene.objects):
        if o.type == "MESH" and o.modifiers:
            evaluated = o.evaluated_get(depsgraph)
            o.data = bpy.data.meshes.new_from_object(evaluated)
            o.modifiers.clear()
    for o in scene.objects:
        if o.type != "MESH" or not o.data.materials:
            continue
        if o.get("asset_uv"):
            continue
        if not o.data.uv_layers:
            o.data.uv_layers.new(name="UVMap")
        uv = o.data.uv_layers.get("UVMap") or o.data.uv_layers[0]
        uv.name = "UVMap"
        if o.get("detail") and "tex_scale" not in o.data.materials[0]:
            continue
        for poly in o.data.polygons:
            material = o.data.materials[poly.material_index]
            scale = material.get("tex_scale", 1.6)
            n = o.matrix_world.to_3x3() @ poly.normal
            axis = max(range(3), key=lambda k: abs(n[k]))
            axes = [k for k in range(3) if k != axis]
            for li in poly.loop_indices:
                p = o.matrix_world @ o.data.vertices[o.data.loops[li].vertex_index].co
                uv.data[li].uv = (p[axes[0]] / scale, p[axes[1]] / scale)
        for m in o.data.materials:
            if not m.use_nodes:
                continue
            for n in list(m.node_tree.nodes):
                if n.type == "TEX_IMAGE" and not n.inputs["Vector"].is_linked:
                    uvn = m.node_tree.nodes.new("ShaderNodeUVMap")
                    uvn.uv_map = "UVMap"
                    m.node_tree.links.new(uvn.outputs[0], n.inputs["Vector"])
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == "OPTIX"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 3
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(P / "cleveland-realism.blend"))
    # The navigation export is created after the non-overlapping lightmap unwrap.
    (OUT / "collision-realism.json").write_text(json.dumps(collision))
    print(
        "REALISM_SCENE_READY",
        len(scene.objects),
        sum(len(o.data.polygons) for o in scene.objects if o.type == "MESH"),
        flush=True,
    )

    (OUT / "model-realism.json").write_text(json.dumps(D, indent=2))
    return {}
