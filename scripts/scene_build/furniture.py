"""Furniture stage of the reproducible scene build."""

import bpy, math
from mathutils import Vector


def build(
    *,
    asset_templates,
    collision,
    bluecloth,
    box,
    iron,
    leather,
    linen,
    material,
    mesh,
    place_asset,
    remove_prefix,
    rod,
    scene,
    teak
):
    # Linen curtains with modeled folds frame the principal living room window.
    for y0 in [14.8, 17.8]:
        vs = []
        fs = []
        for j in range(33):
            y = y0 + j * 0.024
            x = 12.39 + 0.045 * math.sin(j * math.pi / 2)
            vs.extend([(x, y, 0.84), (x, y, 3.46)])
        for j in range(32):
            fs.append((2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2))
        mesh("Living folded linen curtain", vs, fs, linen)
    # Replace the block sofa with proportioned padded seats, piping, feet and throws.
    remove_prefix(["Sofa", "Leather seat cushion"])
    box(
        "Living leather sofa base",
        (16.04, 18.45, 1.13),
        (0.85, 2.58, 0.35),
        leather,
        0.09,
        True,
    )
    box(
        "Living leather sofa back",
        (16.38, 18.45, 1.63),
        (0.20, 2.55, 0.76),
        leather,
        0.09,
    )
    for j in range(3):
        yy = 17.61 + j * 0.83
        box("Leather seat", (15.96, yy, 1.40), (0.70, 0.79, 0.19), leather, 0.08)
        box(
            "Leather back cushion",
            (16.25, yy, 1.76),
            (0.23, 0.77, 0.58),
            leather,
            0.095,
        )
        for zz in [1.46, 2.0]:
            rod(
                "Sofa stitched piping",
                (16.12, yy - 0.34, zz),
                (16.12, yy + 0.34, zz),
                0.004,
                teak,
            )
    for yy in [17.11, 19.79]:
        box(
            "Leather rolled sofa arm",
            (16.04, yy, 1.51),
            (0.88, 0.19, 0.39),
            leather,
            0.085,
        )
    for xx in [15.76, 16.31]:
        for yy in [17.35, 19.55]:
            box("Sofa feet", (xx, yy, 0.94), (0.065, 0.065, 0.23), teak, 0.009)
    # Framed artworks use the user's listing photos only as observational evidence,
    # never as pasted flat substitutes for geometry.
    chair_template = next(
        o for n, o in asset_templates.items() if n.startswith("chinese_armchair")
    )
    # Replace the two simple living-room chairs with curved wooden frames and cushions.
    for o in list(scene.objects):
        if o.name.startswith("Chair"):
            center = o.matrix_world @ (
                sum((Vector(c) for c in o.bound_box), Vector()) / 8
            )
            if 12.9 < center.x < 13.6 and 15 < center.y < 16.9:
                bpy.data.objects.remove(o, do_unlink=True)
    for y in [15.4, 16.5]:
        place_asset(
            chair_template,
            "Living curved wood armchair",
            (13.3, y, 0.8),
            (0.68, 0.7, 1.05),
            -math.pi / 2,
        )
        box(
            "Armchair linen seat cushion",
            (13.3, y, 1.24),
            (0.54, 0.53, 0.12),
            linen,
            0.05,
        )
    for x, y, z, w, h in [
        (16.89, 18.7, 2.65, 1.05, 0.7),
        (12.61, 24.5, 2.55, 0.85, 0.65),
    ]:
        box("Oak picture frame", (x, y, z), (0.045, w, h), teak, 0.012)
        art = material("Muted abstract artwork " + str(y), (0.30, 0.37, 0.25), 0.95)
        box("Artwork", (x - 0.025, y, z), (0.01, w - 0.07, h - 0.07), art)
    # Outdoor chaise lounges and a scalloped blue umbrella match the pool photographs.
    for y in [34.4, 35.35]:
        box(
            "Pool chaise cushion",
            (10.95, y, 0.38),
            (1.8, 0.61, 0.12),
            bluecloth,
            0.06,
            True,
        )
        back = box(
            "Raised chaise back", (10.3, y, 0.62), (0.66, 0.61, 0.10), bluecloth, 0.05
        )
        back.rotation_euler.y = -0.52
        for x in [10.3, 11.6]:
            rod("Chaise leg", (x, y - 0.24, 0.04), (x, y - 0.24, 0.34), 0.023, iron)
            rod("Chaise leg", (x, y + 0.24, 0.04), (x, y + 0.24, 0.34), 0.023, iron)
    rod("Umbrella mast", (9.9, 27.6, 0.4), (9.9, 27.6, 3.0), 0.035, iron)
    vs = [(9.9, 27.6, 3.04)] + [
        (
            9.9 + 1.4 * math.cos(j * math.tau / 12),
            27.6 + 1.4 * math.sin(j * math.tau / 12),
            2.65,
        )
        for j in range(12)
    ]
    mesh(
        "Blue terrace umbrella",
        vs,
        [(0, j + 1, (j + 1) % 12 + 1) for j in range(12)],
        bluecloth,
    )
    for j in range(12):
        rod("Umbrella rib", vs[0], vs[j + 1], 0.009, iron)
    collision[:] = [
        block for block in collision if not block["name"].startswith("Outdoor table")
    ]
    # Photo 51/52: dining furniture belongs on the recessed lower terrace.
    # The former table occupied the curved upper planting terrace.
    for obj in list(scene.objects):
        center = obj.matrix_world @ (
            sum((Vector(c) for c in obj.bound_box), Vector()) / 8
        )
        if obj.name.startswith("Outdoor table") or (
            obj.name.startswith("Chair")
            and 12.7 < center.x < 15.6
            and 26.6 < center.y < 29.7
        ):
            bpy.data.objects.remove(obj, do_unlink=True)
    box(
        "Lower terrace dining table",
        (10.0, 27.65, 1.14),
        (1.25, 0.83, 0.055),
        iron,
        0.025,
        True,
    )
    for x in [9.52, 10.48]:
        for y in [27.36, 27.94]:
            rod("Terrace table leg", (x, y, 0.4), (x, y, 1.12), 0.018, iron)
    for x, y, angle in [
        (9.1, 27.65, -math.pi / 2),
        (10.9, 27.65, math.pi / 2),
        (10, 26.85, 0),
        (10, 28.45, math.pi),
    ]:
        box("Terrace woven chair seat", (x, y, 0.86), (0.48, 0.48, 0.065), iron, 0.025)
        for dx in [-0.18, 0.18]:
            for dy in [-0.18, 0.18]:
                rod(
                    "Terrace chair leg",
                    (x + dx, y + dy, 0.4),
                    (x + dx, y + dy, 0.86),
                    0.014,
                    iron,
                )
        back = box(
            "Terrace woven chair back",
            (x, y + 0.20, 1.10),
            (0.46, 0.045, 0.46),
            iron,
            0.025,
        )
        back.rotation_euler.z = angle
    return {}
