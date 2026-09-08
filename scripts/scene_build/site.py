"""Site stage of the reproducible scene build."""

import math
from mathutils import Vector


def build(
    *,
    F,
    collision,
    O,
    box,
    fence,
    iron,
    line,
    remove_prefix,
    rod,
    roofwhite,
    scene,
    slate,
    stone,
    terrace,
    white
):
    remove_prefix(["Leaves", "Trunk", "Branch", "Validation sealed room"])
    collision[:] = [c for c in collision if not c["name"].startswith("Trunk")]
    # Rear wings have light-colored roofs; the main hip surrounds a flat white center.
    for o in scene.objects:
        if o.name.startswith("Roof deck"):
            o.data.materials.clear()
            o.data.materials.append(roofwhite)
        if o.name == "Hip roof":
            o.data.materials.append(roofwhite)
            o.data.polygons[-1].material_index = 1
        if "terrace" in o.name.lower() or o.name.startswith("Terrace step"):
            if any(m and m.name.startswith("Terracotta") for m in o.data.materials):
                o.data.materials.clear()
                o.data.materials.append(terrace)
                o.data.materials.append(white)
                for p in o.data.polygons:
                    p.material_index = 0 if p.normal.z > 0.5 else 1

    # Fence is visible behind the pool and on both planted boundaries (photos 45-52).
    def privacy(a, b, height=1.9):
        a = Vector(a)
        b = Vector(b)
        d = b - a
        L = d.length
        u = d / L
        line("Privacy fence panel", a, b, 0, height, 0.06, fence)
        collision.append(
            {
                "name": "Privacy fence barrier",
                "min": [min(a.x, b.x) - 0.04, min(a.y, b.y) - 0.04, 0],
                "max": [max(a.x, b.x) + 0.04, max(a.y, b.y) + 0.04, height],
            }
        )
        for j in range(math.ceil(L / 0.145)):
            p = a + u * min(L, j * 0.145)
            line("Fence board seam", p, p + u * 0.018, 0, height, 0.071, fence)
        for j in range(math.ceil(L / 2.1) + 1):
            p = a + u * min(L, j * 2.1)
            box(
                "Fence post",
                (p.x, p.y, height / 2),
                (0.12, 0.12, height + 0.08),
                fence,
                0.012,
            )
        line("Fence top rail", a, b, height - 0.09, 0.12, 0.12, fence)

    privacy((-0.12, 16), (-0.22, 37.1))
    privacy((-0.22, 37.1), (20.85, 37.1))
    privacy((20.85, 16), (20.85, 37.1))
    # Low stucco retaining walls, substantial coping and terrace railings.
    for a, b in [
        ((0.3, 29.7), (0.3, 35.9)),
        ((0.3, 35.9), (12.4, 35.9)),
        ((16.3, 27.3), (19.5, 28.1)),
        ((19.5, 28.1), (20.2, 35.5)),
    ]:
        line("Garden retaining wall", a, b, 0, 0.55, 0.28, white)
        line("Garden wall coping", a, b, 0.55, 0.07, 0.34, stone)
    for a, b in [
        ((11.55, 26.45), (11.55, 29.25)),
        ((11.55, 29.25), (12.8, 30.6)),
        ((14.9, 30.6), (16.2, 29.2)),
    ]:
        a = Vector(a)
        b = Vector(b)
        u = (b - a).normalized()
        L = (b - a).length
        for j in range(math.ceil(L / 0.14) + 1):
            p = a + u * min(L, j * 0.14)
            rod("Fine terrace picket", (*p, 0.82), (*p, 1.69), 0.009, iron)
        rod("Terrace top rail", (*a, 1.71), (*b, 1.71), 0.024, iron)
    # Front approach, porch joinery and planting beds.
    for yy in [7.2, 7.8, 8.4, 9.0, 9.6]:
        box(
            "Front approach flagstone",
            (10.75, yy, 0.035),
            (1.48, 0.56, 0.045),
            slate,
            0.025,
        )
    for z, y in [(0.2, 10.1), (0.4, 10.4), (0.6, 10.7)]:
        box("Front entry step", (10.75, y, z / 2), (1.65, 0.35, z), stone, 0.025)
    box("Front door", (10.72, 13.42, 1.84), (1.15, 0.07, 2.1), iron, 0.015)
    for x in [10.39, 11.03]:
        for z in [1.1, 1.8, 2.5]:
            box(
                "Front door raised panel",
                (x, 13.365, z),
                (0.47, 0.045, 0.52),
                fence,
                0.012,
            )
    for x in [8.4, 17.1, 19.9]:
        box("Porch column plinth", (x, 10.6, 0.45), (0.38, 0.38, 0.9), white, 0.015)
        box("Porch column capital", (x, 10.6, 3.08), (0.39, 0.39, 0.18), white, 0.014)
    # Neighbor footprints are retained from the supplied geospatial geometry.
    # Roofs, cornices and regular windows add plausible detail without claiming survey accuracy.
    for ni, b in enumerate(O["neighbors"]):
        pts = [Vector((x * F, y * F)) for x, y in b["ring"]]
        cx = sum(p.x for p in pts) / len(pts)
        cy = sum(p.y for p in pts) / len(pts)
        if math.hypot(cx - 10, cy - 20) > 65:
            continue
        for a, bb in zip(pts, pts[1:]):
            d = bb - a
            L = d.length
            if L < 2:
                continue
            line("Neighbor roof cornice", a, bb, 8.8, 0.25, 0.3, stone)
            u = d / L
            normal = Vector((-u.y, u.x))
            mid = (a + bb) / 2
            if normal.dot(mid - Vector((cx, cy))) < 0:
                normal = -normal
            for j in range(1, int(L / 2.3) + 1):
                p = a + u * (j * L / (int(L / 2.3) + 1)) + normal * 0.025
                for z in [2.2, 5.2]:
                    win = line(
                        "Neighbor recessed window",
                        p - u * 0.42,
                        p + u * 0.42,
                        z - 0.65,
                        1.3,
                        0.04,
                        iron,
                    )
                    line(
                        "Neighbor window lintel",
                        p - u * 0.48,
                        p + u * 0.48,
                        z + 0.65,
                        0.08,
                        0.15,
                        stone,
                    )
    return {"collision": collision}
