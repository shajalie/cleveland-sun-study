"""Geometry stage of the reproducible scene build."""

import bpy, math
from mathutils import Vector


def build(*, I, collision, scene):
    def finish(o, name, m, solid=False, detail=False):
        o.name = name
        o.data.materials.clear()
        o.data.materials.append(m)
        o["solid"] = solid
        o["detail"] = detail
        if solid:
            bpy.context.view_layer.update()
            pts = [o.matrix_world @ Vector(v) for v in o.bound_box]
            collision.append(
                {
                    "name": name,
                    "min": [min(p[k] for p in pts) for k in range(3)],
                    "max": [max(p[k] for p in pts) for k in range(3)],
                }
            )
        return o

    def box(name, p, s, m, bevel=0, solid=False):
        x, y, z = p
        a, b, c = [v / 2 for v in s]
        vs = [
            (x + dx * a, y + dy * b, z + dz * c)
            for dx, dy, dz in [
                (-1, -1, -1),
                (1, -1, -1),
                (1, 1, -1),
                (-1, 1, -1),
                (-1, -1, 1),
                (1, -1, 1),
                (1, 1, 1),
                (-1, 1, 1),
            ]
        ]
        o = mesh(
            name,
            vs,
            [
                (3, 2, 1, 0),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
                (4, 5, 6, 7),
            ],
            m,
        )
        # Keep local coordinates centered so later rotations remain meaningful.
        for vertex in o.data.vertices:
            vertex.co -= Vector(p)
        o.location = p
        if solid:
            o["solid"] = True
            collision.append(
                {
                    "name": name,
                    "min": [p[k] - s[k] / 2 for k in range(3)],
                    "max": [p[k] + s[k] / 2 for k in range(3)],
                }
            )
        if bevel:
            mod = o.modifiers.new("Rounded edges", "BEVEL")
            mod.width = bevel
            mod.segments = 8
            mod.harden_normals = True
            for face in o.data.polygons:
                face.use_smooth = True
            normals = o.modifiers.new("Weighted surface normals", "WEIGHTED_NORMAL")
            normals.keep_sharp = True
        return o

    RODS = {}

    def rod(name, a, b, r, m, r2=None, detail=False):
        a = Vector(a)
        b = Vector(b)
        d = (b - a).normalized()
        u = d.cross(Vector((0, 0, 1)))
        if u.length < 0.01:
            u = d.cross(Vector((0, 1, 0)))
        u.normalize()
        v = d.cross(u)
        vs = [
            p
            + (u * math.cos(j * math.tau / 8) + v * math.sin(j * math.tau / 8)) * radius
            for p, radius in [(a, r), (b, r if r2 is None else r2)]
            for j in range(8)
        ]
        fs = [(j, (j + 1) % 8, (j + 1) % 8 + 8, j + 8) for j in range(8)] + [
            tuple(range(7, -1, -1)),
            tuple(range(8, 16)),
        ]
        if detail:
            av, af = RODS.setdefault(m.name, ([], []))
            base = len(av)
            av.extend(vs)
            af.extend(tuple(base + i for i in f) for f in fs)
            return
        return mesh(name, vs, fs, m)

    def mesh(name, verts, faces, m, detail=False):
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.update()
        o = bpy.data.objects.new(name, me)
        scene.collection.objects.link(o)
        return finish(o, name, m, detail=detail)

    def line(name, a, b, z, h, w, m):
        a = Vector(a)
        b = Vector(b)
        d = b - a
        o = box(
            name, ((a.x + b.x) / 2, (a.y + b.y) / 2, z + h / 2), (d.length, w, h), m
        )
        o.rotation_euler.z = math.atan2(d.y, d.x)
        return o

    def inside(p, poly):
        hit = False
        for a, b in zip(poly, poly[-1:] + poly[:-1]):
            if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0] - a[0]) * (
                p[1] - a[1]
            ) / (b[1] - a[1]) + a[0]:
                hit = not hit
        return hit

    def occupied(x, y, z):
        return z < 8.6 and any(inside((x, y), f["outline"]) for f in I["floors"])

    def remove_prefix(prefixes):
        for o in list(scene.objects):
            if any(o.name.startswith(p) for p in prefixes):
                bpy.data.objects.remove(o, do_unlink=True)

    return {
        "finish": finish,
        "box": box,
        "rod": rod,
        "mesh": mesh,
        "line": line,
        "inside": inside,
        "occupied": occupied,
        "remove_prefix": remove_prefix,
        "RODS": RODS,
    }
