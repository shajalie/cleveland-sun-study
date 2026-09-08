"""Physically scaled scanned detail, shared by Cycles and the navigation export."""

import json
import math
import bpy
import numpy as np


def apply_scan(material, directory, asset, *, scale=None, color=True, strength=1.0):
    record = json.loads((directory / (asset + ".json")).read_text())
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    retained_color = (
        shader.inputs["Base Color"].links[0].from_node
        if not color and shader.inputs["Base Color"].is_linked
        else None
    )
    for node in list(nodes):
        if node is retained_color:
            continue
        if node.type in {"TEX_IMAGE", "NORMAL_MAP", "UVMAP"}:
            nodes.remove(node)
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    if retained_color and retained_color.type == "TEX_IMAGE":
        links.new(uv.outputs["UV"], retained_color.inputs["Vector"])
    for channel, socket in [
        ("diff", "Base Color"),
        ("rough", "Roughness"),
        ("normal", "Normal"),
    ]:
        if channel == "diff" and not color:
            continue
        item = record["files"].get(channel)
        if not item:
            continue
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = bpy.data.images.load(
            str(directory / item["file"]), check_existing=True
        )
        texture.interpolation = "Linear"
        links.new(uv.outputs["UV"], texture.inputs["Vector"])
        if channel != "diff":
            texture.image.colorspace_settings.name = "Non-Color"
        if channel == "normal":
            normal = nodes.new("ShaderNodeNormalMap")
            # Explicit tangents are essential after a separate lightmap UV is added.
            normal.uv_map = "UVMap"
            normal.inputs["Strength"].default_value = strength
            links.new(texture.outputs["Color"], normal.inputs["Color"])
            links.new(normal.outputs["Normal"], shader.inputs[socket])
        else:
            links.new(texture.outputs["Color"], shader.inputs[socket])
    dimensions = record.get("dimensionsMillimeters") or [1000, 1000]
    material["tex_scale"] = scale if scale is not None else dimensions[0] / 1000
    material["surface_source"] = record["source"]
    material["surface_resolution"] = 2048


def build(output):
    directory = output / "textures/detail"
    specifications = [
        ("Modeled terracotta clay", "white_stucco", 0.75, False, 0.5),
        ("Dark charcoal painted privacy fence", "fine_grained_wood", 0.8, False, 0.8),
        ("White rear roof membrane", "concrete_floor_worn_001", 3.0, False, 0.35),
        ("Honey oak furniture", "fine_grained_wood", 0.8, True, 1.0),
        ("Dark wood trim", "fine_grained_wood", 0.8, False, 0.7),
        ("Upholstery", "fabric_pattern_05", 0.5, False, 0.8),
        ("Muted woven rug", "fabric_pattern_05", 0.5, False, 0.65),
        ("Plaster", "white_stucco", None, True, 1.25),
        ("Warm ivory exterior stucco", "white_stucco", 1.25, True, 1.5),
        ("Ceiling", "white_stucco", 2.0, True, 0.75),
        ("Cognac leather", "brown_leather", 0.4, True, 1.0),
        ("Natural linen curtains", "fabric_pattern_05", 0.5, False, 0.8),
        ("Ivory linen", "quatrefoil_jacquard_fabric", 0.65, True, 0.85),
        ("Blue woven outdoor cushions", "fabric_pattern_05", 0.5, False, 0.9),
        ("Limestone paving", "concrete_floor_worn_001", 2.0, True, 1.1),
        ("Pale stone garden walls", "concrete_floor_worn_001", 2.0, True, 1.1),
        ("Blue gray flagstones", "red_sandstone_pavement", 2.15, False, 1.15),
        ("Neighbor gray slate roof", "grey_roof_tiles", 2.0, True, 1.0),
    ]
    for prefix, asset, scale, color, strength in specifications:
        for material in bpy.data.materials:
            if material.name.startswith(prefix):
                apply_scan(
                    material,
                    directory,
                    asset,
                    scale=scale,
                    color=color,
                    strength=strength,
                )
    # Living armchairs in the photographs have patterned fabric upholstery.
    upholstery = bpy.data.materials.new("Patterned armchair upholstery")
    upholstery.use_nodes = True
    apply_scan(upholstery, directory, "quatrefoil_jacquard_fabric", scale=0.65)
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.name.startswith("Armchair linen seat cushion"):
            obj.data.materials.clear()
            obj.data.materials.append(upholstery)
    lawn = bpy.data.objects.get("Individual lawn blades")
    if lawn:
        colors = lawn.data.color_attributes.new(
            name="Natural grass variation", type="FLOAT_COLOR", domain="CORNER"
        )
        values = np.ones((len(lawn.data.loops), 4), np.float32)
        for face in lawn.data.polygons:
            for index, loop_index in enumerate(face.loop_indices):
                p = lawn.data.vertices[lawn.data.loops[loop_index].vertex_index].co
                patch = (
                    0.5
                    + 0.25 * math.sin(p.x * 2.1 + p.y * 0.7)
                    + 0.25 * math.sin(p.y * 3.4 - p.x * 0.9)
                )
                light = 0.65 if index < 2 else 1.05
                values[loop_index, :3] = (
                    np.array(
                        (
                            0.03 + 0.035 * patch,
                            0.065 + 0.06 * patch,
                            0.009 + 0.015 * patch,
                        )
                    )
                    * light
                )
        colors.data.foreach_set("color", values.ravel())
        nodes = lawn.data.materials[0].node_tree.nodes
        color = nodes.new("ShaderNodeVertexColor")
        color.layer_name = colors.name
        lawn.data.materials[0].node_tree.links.new(
            color.outputs["Color"], nodes.get("Principled BSDF").inputs["Base Color"]
        )
    print(
        "SURFACE_DETAIL_READY",
        sum(bool(m.get("surface_source")) for m in bpy.data.materials),
        flush=True,
    )
