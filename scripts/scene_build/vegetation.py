"""Vegetation stage of the reproducible scene build."""

import bpy, bmesh, math
import numpy as np
from mathutils import Vector


def build(
    *,
    F,
    I,
    O,
    P,
    bark,
    burgundy,
    collision,
    deciduous,
    green,
    inside,
    mesh,
    occupied,
    pink,
    rng,
    rod,
    scene
):
    def crown(name, x, y, top, r, evergreen=False, mat=None):
        mat = mat or (green if evergreen else deciduous)
        verts = []
        faces = []
        colors = []
        rod(
            name + " trunk",
            (x, y, 0),
            (x, y, top * 0.93 if evergreen else top * 0.72),
            0.16 if top > 8 else 0.08,
            bark,
            0.035,
        )
        collision.append(
            {
                "name": name + " trunk",
                "min": [x - 0.18, y - 0.18, 0],
                "max": [x + 0.18, y + 0.18, top * 0.7],
            }
        )
        branch_count = 48 if evergreen else 32
        for j in range(branch_count):
            t = (j + 0.5) / branch_count
            az = j * 2.39996 + rng.uniform(-0.3, 0.3)
            z = (0.17 + 0.76 * t) * top if evergreen else (0.35 + 0.45 * t) * top
            reach = (
                r * (1 - t) ** 0.65
                if evergreen
                else r * (0.45 + 0.55 * math.sin(t * math.pi))
            )
            a = Vector((x, y, z))
            end = a + Vector(
                (
                    math.cos(az) * reach,
                    math.sin(az) * reach,
                    -0.10 * top if evergreen else 0.13 * top,
                )
            )
            if occupied(end.x, end.y, end.z):
                continue
            rod(name + " primary branch", a, end, 0.035, bark, 0.008, True)
            for k in range(13):
                q = (k + 0.5) / 13
                center = a.lerp(end, q)
                side = Vector((-math.sin(az), math.cos(az), 0))
                for sign in [-1, 1]:
                    tip = (
                        center
                        + side * sign * reach * 0.30 * (1 - q)
                        + Vector((0, 0, 0.1))
                    )
                    rod(name + " twig", center, tip, 0.007, bark, 0.002, True)
                    for leaf_i in range(14 if evergreen else 11):
                        p = center.lerp(tip, rng.random()) + Vector(
                            (
                                rng.uniform(-0.16, 0.16),
                                rng.uniform(-0.16, 0.16),
                                rng.uniform(-0.16, 0.16),
                            )
                        )
                        if occupied(p.x, p.y, p.z):
                            continue
                        ang = rng.uniform(0, math.tau)
                        size = (
                            rng.uniform(0.07, 0.15)
                            if evergreen
                            else rng.uniform(0.055, 0.095)
                        )
                        u = (
                            Vector(
                                (math.cos(ang), math.sin(ang), rng.uniform(-0.5, 0.5))
                            )
                            * size
                        )
                        v = (
                            Vector(
                                (-math.sin(ang), math.cos(ang), rng.uniform(-0.4, 0.4))
                            )
                            * size
                            * (0.60 if evergreen else 0.65)
                        )
                        base = len(verts)
                        verts.extend(
                            [
                                p - u,
                                p - v * 0.7,
                                p + Vector((0, 0, size * 0.15)),
                                p + v * 0.7,
                                p + u,
                            ]
                        )
                        faces.extend(
                            [
                                (base, base + 1, base + 2),
                                (base + 1, base + 4, base + 2),
                                (base + 4, base + 3, base + 2),
                                (base + 3, base, base + 2),
                            ]
                        )
        o = mesh(name + " foliage", verts, faces, mat, True)
        o["tree"] = True
        o["evergreen"] = evergreen
        o["tree_center"] = [x, y, top * 0.6]

    with bpy.data.libraries.load(
        str(P / ".runtime/realism-assets.blend"), link=False
    ) as (source, dest):
        dest.objects = [n for n in source.objects]
    asset_templates = {o.name: o for o in dest.objects if o and o.type == "MESH"}

    def place_asset(template, name, p, dimensions, angle=0):
        o = template.copy()
        o.data = template.data
        scene.collection.objects.link(o)
        o.name = name
        low = Vector([min(v[k] for v in template.bound_box) for k in range(3)])
        high = Vector([max(v[k] for v in template.bound_box) for k in range(3)])
        o.parent = None
        o.rotation_euler = (0, 0, angle)
        o.scale = Vector(
            [dimensions[k] / max(0.001, high[k] - low[k]) for k in range(3)]
        )
        center = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
        o.location = Vector(p) - o.rotation_euler.to_matrix() @ Vector(
            [center[k] * o.scale[k] for k in range(3)]
        )
        o["asset_uv"] = True
        return o

    fir = [o for n, o in asset_templates.items() if n.startswith("fir_tree")]
    broad = next(o for n, o in asset_templates.items() if n.startswith("tree_small"))

    def subset(source, keep_leaf):
        me = source.copy()
        bm = bmesh.new()
        bm.from_mesh(me)
        indices = {
            i for i, m in enumerate(source.materials) if "leaves" in m.name.lower()
        }
        assert indices, "Deciduous leaf material not identified"
        bmesh.ops.delete(
            bm,
            geom=[f for f in bm.faces if (f.material_index in indices) != keep_leaf],
            context="FACES",
        )
        bmesh.ops.delete(
            bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS"
        )
        bm.to_mesh(me)
        bm.free()
        return me

    broad_leaves = subset(broad.data, True)
    broad_branches = subset(broad.data, False)

    def prune_asset(o):
        bpy.context.view_layer.update()
        verts = np.empty(len(o.data.vertices) * 3, np.float32)
        o.data.vertices.foreach_get("co", verts)
        verts = verts.reshape(-1, 3)
        mat = np.array(o.matrix_world)
        xyz = verts @ mat[:3, :3].T + mat[:3, 3]
        mask = np.zeros(len(verts), bool)
        for floor in I["floors"]:
            poly = floor["outline"]
            inside_mask = np.zeros(len(verts), bool)
            x = xyz[:, 0]
            y = xyz[:, 1]
            for a, b in zip(poly, poly[-1:] + poly[:-1]):
                if a[1] == b[1]:
                    continue
                inside_mask ^= ((a[1] > y) != (b[1] > y)) & (
                    x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
                )
            mask |= inside_mask & (xyz[:, 2] < 8.6)
        if not mask.any():
            return
        o.data = o.data.copy()
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.verts.ensure_lookup_table()
        bad = [v for v in bm.verts if mask[v.index]]
        bmesh.ops.delete(bm, geom=bad, context="VERTS")
        bm.to_mesh(o.data)
        bm.free()
        print("PRUNED_BUILDING_INTRUSION", o.name, len(bad), flush=True)

    for i, t in enumerate(O["trees"]):
        x, y, r, top = t
        x *= F
        y *= F
        r *= F
        evergreen = i in [0, 1, 7, 8, 9, 10, 11, 12, 13]
        template = fir[i % len(fir)] if evergreen else broad
        o = place_asset(
            template,
            ("Evergreen" if evergreen else "Deciduous") + " " + str(i),
            (x, y, 0),
            (2 * r, 2 * r, top),
            rng.random() * math.tau,
        )
        o["tree"] = True
        o["evergreen"] = evergreen
        o["detail"] = True
        o["tree_center"] = [x, y, top * 0.6]
        if not evergreen:
            branch = o.copy()
            branch.data = broad_branches
            branch.name = "Deciduous persistent branches " + str(i)
            branch["tree"] = False
            scene.collection.objects.link(branch)
            o.data = broad_leaves
            prune_asset(branch)
        prune_asset(o)
        collision.append(
            {
                "name": o.name + " trunk",
                "min": [x - 0.18, y - 0.18, 0],
                "max": [x + 0.18, y + 0.18, top * 0.7],
            }
        )
        print("TREE_READY", i, flush=True)
    # Purple-leaf ornamental maple beside the rear wing and layered azalea planting.
    crown("Rear ornamental maple", 18.0, 27.0, 4.0, 1.4, False, burgundy)
    for i, (x, y, r, h) in enumerate(
        [
            (5.5, 9, 1.1, 1.25),
            (7.0, 9.3, 1.0, 1.1),
            (8.4, 9.5, 1, 1.2),
            (13, 9.4, 1.3, 1.4),
            (15, 9.4, 1.25, 1.3),
            (17, 9, 1.1, 1.2),
            (18.5, 27.5, 1.0, 1.9),
            (19.6, 30, 1.0, 2),
            (1, 27.8, 0.8, 1.2),
        ]
    ):
        crown("Shrub " + str(i), x, y, h, r, True, deciduous)
        if y < 10:
            vs = []
            fs = []
            for j in range(210):
                az = rng.random() * math.tau
                u = rng.uniform(-0.4, 1)
                rr = r * math.sqrt(1 - u * u)
                p = Vector(
                    (
                        x + rr * math.cos(az),
                        y + rr * math.sin(az),
                        h * 0.55 + u * h * 0.45,
                    )
                )
                q = len(vs)
                vs.extend(
                    [
                        p
                        + Vector(
                            (
                                math.cos(k * math.tau / 5) * 0.052,
                                math.sin(k * math.tau / 5) * 0.052,
                                0.018 * (k % 2),
                            )
                        )
                        for k in range(5)
                    ]
                )
                fs.append(tuple(range(q, q + 5)))
            o = mesh("Spring azalea blossoms " + str(i), vs, fs, pink, True)
            o["spring_only"] = True
    # Individual lawn blades are batched into one mesh, with pathways kept clear.
    vs = []
    fs = []
    for j in range(700000):
        x = rng.uniform(0.2, 20.5)
        y = rng.uniform(0.2, 36.8)
        lawn = inside((x / F, y / F), O["zones"][7]["poly"]) or inside(
            (x / F, y / F), O["zones"][2]["poly"]
        )
        if not lawn or (10 < x < 11.6 and 7 < y < 10.5):
            continue
        for k in range(3):
            a = rng.random() * math.tau
            h = rng.uniform(0.020, 0.045)
            u = Vector((math.cos(a), math.sin(a), 0)) * 0.006
            p = Vector((x, y, 0.022))
            q = len(vs)
            vs.extend([p - u, p + u, p + Vector((u.x * 3, u.y * 3, h))])
            fs.append((q, q + 1, q + 2))
    mesh("Individual lawn blades", vs, fs, deciduous, True)
    return {"asset_templates": asset_templates, "place_asset": place_asset}
