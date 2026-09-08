"""Architectural corrections checked against Compass photos 0–4, 51 and 54.

Dimensions remain inferred where the listing supplies no measurement. In particular,
the porch parapet must occlude the lower part of the upper-front windows.
"""

import math
import bpy
from mathutils import Vector


def bounds_center(obj):
    return obj.matrix_world @ (sum((Vector(c) for c in obj.bound_box), Vector()) / 8)


def rebuild_front_porch(box, line, white, stone, iron, collision):
    """Replace the thin canopy with the raised porch, entablature and parapet."""
    prefixes = (
        "Porch column",
        "Front porch",
        "Covered porch",
        "Carport",
        "Front entry step",
        "Front approach flagstone",
    )
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)
    collision[:] = [item for item in collision if not item["name"].startswith(prefixes)]
    # The supplied GIS outline places the porch from x=8.4 to 20.1 m.
    box("Front porch raised paving", (12.75, 12.05, 0.69), (8.7, 3.1, 0.22), stone)
    box("Carport driveway", (18.7, 12.85, 0.025), (2.8, 5.7, 0.05), stone)
    box("Front porch roof", (14.3, 12.05, 4.12), (12.15, 3.25, 0.25), white)
    # A three-layer cornice, repeated dentils, and substantial square columns.
    for z, thickness, depth in [
        (3.85, 0.18, 0.50),
        (4.03, 0.12, 0.62),
        (4.21, 0.12, 0.70),
    ]:
        box("Porch entablature", (14.3, 10.48, z), (12.4, depth, thickness), white)
    for x in [8.5, 12.65, 17.0, 20.1]:
        base = 0.78 if x < 17.5 else 0.05
        box(
            "Porch column shaft",
            (x, 10.68, (base + 3.78) / 2),
            (0.49, 0.49, 3.78 - base),
            white,
            0.015,
            True,
        )
        box(
            "Porch column base",
            (x, 10.68, base + 0.10),
            (0.65, 0.65, 0.20),
            white,
            0.018,
        )
        box("Porch column capital", (x, 10.68, 3.73), (0.72, 0.70, 0.22), white, 0.018)
    for x in [8.3 + i * 0.18 for i in range(69)]:
        box("Porch cornice dentil", (x, 10.22, 3.91), (0.065, 0.16, 0.11), white)
    line("Porch balcony parapet", (8.3, 10.46), (20.36, 10.46), 4.24, 0.78, 0.18, white)
    line(
        "Porch parapet dark coping",
        (8.22, 10.46),
        (20.43, 10.46),
        5.02,
        0.055,
        0.25,
        iron,
    )
    for x in [8.3, 20.36]:
        line("Porch side parapet", (x, 10.46), (x, 13.68), 4.24, 0.78, 0.18, white)
        line("Porch side coping", (x, 10.42), (x, 13.72), 5.02, 0.055, 0.25, iron)
    for index in range(4):
        height = (index + 1) * 0.19
        box(
            "Front porch stair",
            (10.6, 9.35 + index * 0.29, height / 2),
            (2.4, 0.32, height),
            stone,
            0.025,
        )
    # Front door remains at its floor-plan location. Right bay stays open for car access.
    for x in [9.35, 11.2, 13.6, 15.6, 18.7]:
        box("Porch hanging lantern", (x, 11.8, 3.46), (0.14, 0.14, 0.26), iron, 0.01)


def replace_rectangular_window(
    wall_index,
    floor_index,
    floor,
    opening_index,
    width,
    sill,
    head,
    box,
    line,
    plaster,
    trim,
    glass,
):
    """Resize one existing opening, filling removed glass area with opaque wall.

    Filling and replacing a window keeps the surrounding wall topology intact.
    It avoids rebuilding unrelated openings or altering navigation geometry.
    """
    wall = floor["walls"][wall_index]
    opening = wall["holes"][opening_index]
    a, b = Vector(opening["a"]), Vector(opening["b"])
    direction = (b - a).normalized()
    center = (a + b) / 2
    old_width = (b - a).length
    old_sill = opening.get("sill", 0.8)
    old_head = opening.get("head", 2.4)
    base = floor["base"]
    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH" or not obj.name.startswith(
            ("Glass", "Window", "Mullion")
        ):
            continue
        c = bounds_center(obj)
        delta = Vector((c.x, c.y)) - center
        if abs(delta.dot(Vector((-direction.y, direction.x)))) > 0.32:
            continue
        if (
            abs(delta.dot(direction)) > old_width / 2 + 0.12
            or not base + 0.05 < c.z < base + floor["ceiling"]
        ):
            continue
        bpy.data.objects.remove(obj, do_unlink=True)
    left = center - direction * width / 2
    right = center + direction * width / 2
    if old_width > width:
        line(
            "Photo corrected window wall",
            a,
            left,
            base + old_sill,
            old_head - old_sill,
            0.20,
            plaster,
        )
        line(
            "Photo corrected window wall",
            right,
            b,
            base + old_sill,
            old_head - old_sill,
            0.20,
            plaster,
        )
    if sill > old_sill:
        line(
            "Photo corrected window sill infill",
            left,
            right,
            base + old_sill,
            sill - old_sill,
            0.20,
            plaster,
        )
    if head < old_head:
        line(
            "Photo corrected window head infill",
            left,
            right,
            base + head,
            old_head - head,
            0.20,
            plaster,
        )
    line("Glass photo corrected", left, right, base + sill, head - sill, 0.006, glass)
    for p in [left, right]:
        line(
            "Window photo jamb",
            p - direction * 0.035,
            p + direction * 0.035,
            base + sill,
            head - sill,
            0.24,
            trim,
        )
    for z in [base + sill, base + head]:
        line("Window photo horizontal frame", left, right, z - 0.025, 0.05, 0.24, trim)
    divisions = max(2, round(width / 0.34))
    for j in range(1, divisions):
        p = left + direction * (width * j / divisions)
        line(
            "Window photo glazing bar",
            p - direction * 0.012,
            p + direction * 0.012,
            base + sill,
            head - sill,
            0.06,
            trim,
        )
    for j in range(1, 4):
        z = base + sill + (head - sill) * j / 4
        line("Window photo glazing rail", left, right, z - 0.01, 0.02, 0.06, trim)
    opening.update(
        a=list(left),
        b=list(right),
        sill=sill,
        head=head,
        evidence="Compass photos 51/54; opening proportions inferred",
    )


def apply_photo_corrections(data, box, line, white, stone, iron, collision):
    data["navigation"] = {
        "surfaces": [
            {
                "polygon": [
                    [9.4, 9.19 + i * 0.29],
                    [11.8, 9.19 + i * 0.29],
                    [11.8, 9.51 + i * 0.29],
                    [9.4, 9.51 + i * 0.29],
                ],
                "height": (i + 1) * 0.19,
            }
            for i in range(4)
        ]
        + [
            {
                "polygon": [[8.4, 10.5], [17.1, 10.5], [17.1, 13.655], [8.4, 13.655]],
                "height": 0.8,
            }
        ]
    }
    rebuild_front_porch(box, line, white, stone, iron, collision)
    trim = bpy.data.materials.get("Dark wood trim")
    glass = next(m for m in bpy.data.materials if m.name.startswith("Glazing"))
    for opening, width in [(0, 1.30), (1, 1.45), (2, 1.10)]:
        replace_rectangular_window(
            0,
            1,
            data["indoor"]["floors"][1],
            opening,
            width,
            0.9,
            2.3,
            box,
            line,
            white,
            trim,
            glass,
        )
    # Rear bedroom has one narrow double-hung window, not a wall-wide picture window.
    replace_rectangular_window(
        2,
        1,
        data["indoor"]["floors"][1],
        0,
        1.12,
        0.88,
        2.36,
        box,
        line,
        white,
        trim,
        glass,
    )

    # The breakfast-room window beneath the sunroom is also a single narrow unit.
    replace_rectangular_window(
        6,
        0,
        data["indoor"]["floors"][0],
        0,
        1.25,
        0.85,
        2.4,
        box,
        line,
        white,
        trim,
        glass,
    )


def paint_exterior_joinery(data, iron):
    """Keep interior timber faces and paint outward-facing window faces dark."""
    bpy.context.view_layer.update()
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or not obj.name.startswith(("Window", "Mullion")):
            continue
        center = bounds_center(obj)
        candidates = []
        for floor in data["indoor"]["floors"]:
            if not floor["base"] < center.z < floor["base"] + floor["ceiling"]:
                continue
            for wall in floor["walls"]:
                if not wall["ext"]:
                    continue
                a, b = Vector(wall["a"]), Vector(wall["b"])
                d = b - a
                t = max(
                    0,
                    min(
                        1, (Vector((center.x, center.y)) - a).dot(d) / d.length_squared
                    ),
                )
                distance = (Vector((center.x, center.y)) - a - d * t).length
                candidates.append((distance, d.normalized()))
        if not candidates:
            continue
        distance, d = min(candidates, key=lambda c: c[0])
        if distance > 0.35:
            continue
        # Exterior rings run counter-clockwise in the floor-plan coordinate frame.
        outward = Vector((d.y, -d.x, 0))
        slot = len(obj.data.materials)
        obj.data.materials.append(iron)
        for face in obj.data.polygons:
            if (obj.matrix_world.to_3x3() @ face.normal).dot(outward) > 0.2:
                face.material_index = slot


def add_arched_joinery(data, mesh, rod, white, iron):
    """Model curved sash and transom bars visible in front/rear photographs."""
    dining = data["indoor"]["floors"][0]["walls"][0]["holes"][0]
    dining["arch"] = True
    for floor in data["indoor"]["floors"]:
        for wall in floor["walls"]:
            if not wall["ext"]:
                continue
            direction = (Vector(wall["b"]) - Vector(wall["a"])).normalized()
            outward = Vector((direction.y, -direction.x))
            for opening in wall["holes"]:
                if not opening.get("arch") or not opening["window"]:
                    continue
                a, b = Vector(opening["a"]), Vector(opening["b"])
                center = (a + b) / 2
                u = (b - a).normalized()
                width = (b - a).length
                base = floor["base"]
                head = opening.get("head", 2.4)
                rise = min(0.5, width / 2)
                sill = opening.get("sill", 0 if opening.get("floorGlass") else 0.8)
                if opening is dining:
                    # Mask the square upper corners of the inherited front glazing.
                    for j in range(32):
                        x0, x1 = j / 32, (j + 1) / 32
                        p = a.lerp(b, x0)
                        q = a.lerp(b, x1)
                        z0 = (
                            base
                            + head
                            - rise * (1 - math.sqrt(max(0, 1 - (2 * x0 - 1) ** 2)))
                        )
                        z1 = (
                            base
                            + head
                            - rise * (1 - math.sqrt(max(0, 1 - (2 * x1 - 1) ** 2)))
                        )
                        vertices = [
                            (v.x + outward.x * t, v.y + outward.y * t, z)
                            for t in [-0.11, 0.11]
                            for v, z in [
                                (p, z0),
                                (q, z1),
                                (q, base + head),
                                (p, base + head),
                            ]
                        ]
                        mesh(
                            "Dining arch masonry",
                            vertices,
                            [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (3, 2, 6, 7)],
                            white,
                        )
                points = []
                for j in range(49):
                    angle = j * math.pi / 48
                    p = center + u * math.cos(angle) * width / 2 + outward * 0.13
                    points.append(
                        (p.x, p.y, base + head - rise + math.sin(angle) * rise)
                    )
                for a3, b3 in zip(points, points[1:]):
                    rod("Arched window curved sash", a3, b3, 0.025, iron)
                for t in [0.25, 0.5, 0.75]:
                    p = a.lerp(b, t) + outward * 0.13
                    top = base + head - rise * (1 - math.sqrt(1 - (2 * t - 1) ** 2))
                    rod(
                        "Arched window upright",
                        (p.x, p.y, base + sill),
                        (p.x, p.y, top),
                        0.013,
                        iron,
                    )
                for j in range(1, 5):
                    z = base + sill + (head - rise - sill) * j / 4
                    p = a + outward * 0.13
                    q = b + outward * 0.13
                    rod(
                        "Arched window transom",
                        (p.x, p.y, z),
                        (q.x, q.y, z),
                        0.013,
                        iron,
                    )
