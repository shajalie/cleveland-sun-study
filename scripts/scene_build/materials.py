"""Materials stage of the reproducible scene build."""

import bpy


def build(*, OUT):
    def material(name, color, rough=0.65, metal=0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        m.diffuse_color = (*color, 1)
        bs = m.node_tree.nodes.get("Principled BSDF")
        bs.inputs["Base Color"].default_value = (*color, 1)
        bs.inputs["Roughness"].default_value = rough
        bs.inputs["Metallic"].default_value = metal
        return m

    def scanned(m, asset, scale):
        n = m.node_tree.nodes
        l = m.node_tree.links
        bs = n.get("Principled BSDF")
        for node in list(n):
            if node.type in ["TEX_IMAGE", "NORMAL_MAP"]:
                n.remove(node)
        uv = n.new("ShaderNodeUVMap")
        uv.uv_map = "UVMap"
        for channel, socket in [
            ("diff", "Base Color"),
            ("rough", "Roughness"),
            ("nor_gl", "Normal"),
        ]:
            files = list((OUT / "textures/scanned").glob(asset + "_" + channel + ".*"))
            if not files:
                continue
            t = n.new("ShaderNodeTexImage")
            t.image = bpy.data.images.load(str(files[0]), check_existing=True)
            l.new(uv.outputs[0], t.inputs["Vector"])
            if channel != "diff":
                t.image.colorspace_settings.name = "Non-Color"
            if channel == "nor_gl":
                normal = n.new("ShaderNodeNormalMap")
                normal.uv_map = "UVMap"
                normal.inputs["Strength"].default_value = (
                    0.35 if "plaster" in asset else 0.65
                )
                l.new(t.outputs["Color"], normal.inputs["Color"])
                l.new(normal.outputs[0], bs.inputs[socket])
            else:
                l.new(t.outputs["Color"], bs.inputs[socket])
        m["tex_scale"] = scale

    for prefix, asset, scale in [
        ("Oak floor", "wood_floor", 2.4),
        ("Plaster", "plastered_wall_02", 1.4),
        ("Terracotta", "clay_roof_tiles", 2.0),
        ("Neighbor masonry", "brown_brick_02", 2.5),
        ("Bark", "bark_brown_02", 1.3),
    ]:
        for m in bpy.data.materials:
            if m.name.startswith(prefix):
                scanned(m, asset, scale)
    white = material("Warm ivory exterior stucco", (0.72, 0.68, 0.59))
    scanned(white, "plastered_wall_02", 1.4)
    iron = material("Charcoal painted iron", (0.025, 0.030, 0.028), 0.42, 0.5)
    fence = material("Dark charcoal painted privacy fence", (0.046, 0.052, 0.050), 0.75)
    stone = material("Pale stone garden walls", (0.56, 0.52, 0.43))
    scanned(stone, "rocky_terrain_02", 1.8)
    teak = material("Honey oak furniture", (0.30, 0.17, 0.072), 0.38)
    linen = material("Natural linen curtains", (0.74, 0.70, 0.62), 0.88)
    soil = material("Garden mulch", (0.055, 0.033, 0.017), 0.95)
    slate = material("Blue gray flagstones", (0.20, 0.23, 0.24), 0.72)
    roofwhite = material("White rear roof membrane", (0.64, 0.65, 0.62), 0.75)
    bluecloth = material("Blue woven outdoor cushions", (0.12, 0.32, 0.42), 0.85)
    terrace = material("Terracotta terrace floor tiles", (0.35, 0.15, 0.08))
    scanned(terrace, "terracotta_floor_tiles", 1.5)
    green = material("Evergreen needles", (0.07, 0.145, 0.063), 0.86)
    deciduous = material("Broadleaf summer foliage", (0.12, 0.24, 0.060), 0.88)
    burgundy = material("Japanese maple foliage", (0.18, 0.035, 0.025), 0.84)
    pink = material("Spring azalea petals", (0.58, 0.045, 0.22), 0.78)
    bark = next(m for m in bpy.data.materials if m.name == "Bark")
    wood = next(m for m in bpy.data.materials if m.name == "Oak floor")
    leather = next(m for m in bpy.data.materials if m.name == "Cognac leather")
    return {
        "material": material,
        "scanned": scanned,
        "white": white,
        "iron": iron,
        "fence": fence,
        "stone": stone,
        "teak": teak,
        "linen": linen,
        "soil": soil,
        "slate": slate,
        "roofwhite": roofwhite,
        "bluecloth": bluecloth,
        "terrace": terrace,
        "green": green,
        "deciduous": deciduous,
        "burgundy": burgundy,
        "pink": pink,
        "bark": bark,
        "wood": wood,
        "leather": leather,
    }
