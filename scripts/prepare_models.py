"""Create a compact library of scanned assets for the 6 GB RTX 2060."""

import bpy, json
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
for asset in ["fir_tree_01", "tree_small_02", "chinese_armchair"]:
    source = P / ".runtime/model-assets" / asset / (asset + "_1k.gltf")
    if asset == "fir_tree_01":
        gltf = json.loads(source.read_text())
        gltf["scenes"][gltf.get("scene", 0)]["nodes"] = [
            next(i for i, n in enumerate(gltf["nodes"]) if "_b_" in n.get("name", ""))
        ]
        source = source.with_name("fir_navigation.gltf")
        source.write_text(json.dumps(gltf))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(source))
    imported = list(set(bpy.data.objects) - before)
    for o in imported:
        if o.type != "MESH":
            continue
        # Use the selected fir crown consistently; exclude unused source variants.
        if asset == "fir_tree_01" and "_b_" not in o.name:
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        target = 1100000 if asset == "fir_tree_01" else 110000
        if len(o.data.polygons) > target:
            mod = o.modifiers.new("Navigation level of detail", "DECIMATE")
            mod.ratio = target / len(o.data.polygons)
            bpy.ops.object.modifier_apply(modifier=mod.name)
        # Preserve all source UVs and surface textures when assembling the house.
        if o.data.uv_layers:
            o.data.uv_layers[0].name = "UVMap"
        o["asset_uv"] = True
        o["detail"] = asset != "chinese_armchair"
        for m in o.data.materials:
            if m and m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == "TEX_IMAGE" and not n.inputs["Vector"].is_linked:
                        uv = m.node_tree.nodes.new("ShaderNodeUVMap")
                        uv.uv_map = "UVMap"
                        m.node_tree.links.new(uv.outputs[0], n.inputs["Vector"])
        print(
            "ASSET_READY", o.name, len(o.data.polygons), list(o.dimensions), flush=True
        )
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / ".runtime/realism-assets.blend"))
