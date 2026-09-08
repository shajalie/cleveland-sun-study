"""Roofed neighboring shade obstructions based on GIS outlines and the 2025 aerial.

The outlines are sourced; ridge/eave heights and roof pitches are estimates.
"""

import math
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


def build(outdoor, mesh, line, box, material, inside):
    slate = material("Neighbor gray slate roof", (0.075, 0.087, 0.09), 0.82)
    tile = material("Neighbor muted red tile roof", (0.20, 0.065, 0.035), 0.83)
    gutter = material("Neighbor dark metal gutters", (0.07, 0.075, 0.07), 0.48, 0.5)
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith("Neighbor roof cornice"):
            bpy.data.objects.remove(obj, do_unlink=True)
    for neighbor in outdoor["neighbors"]:
        ring = [
            Vector((x * 1200 / 3937, y * 1200 / 3937)) for x, y in neighbor["ring"][:-1]
        ]
        obj = bpy.data.objects.get("Neighbor " + str(neighbor["id"]))
        if obj is None:
            continue
        eave = 6.5
        for vertex in obj.data.vertices:
            if vertex.co.z > 0:
                vertex.co.z = eave
        # Constrained triangles preserve the footprint's concave recesses.
        vertices = list(ring)
        low = [min(p[k] for p in ring) for k in range(2)]
        high = [max(p[k] for p in ring) for k in range(2)]
        for ix in range(math.ceil((high[0] - low[0]) / 0.4)):
            for iy in range(math.ceil((high[1] - low[1]) / 0.4)):
                p = Vector((low[0] + (ix + 0.5) * 0.4, low[1] + (iy + 0.5) * 0.4))
                if inside(p, ring):
                    vertices.append(p)
        boundary = [(i, (i + 1) % len(ring)) for i in range(len(ring))]
        coords, _, faces, *_ = delaunay_2d_cdt(vertices, boundary, [], 1, 0.00001)

        def distance(p):
            distances = []
            for a, b in zip(ring, ring[1:] + ring[:1]):
                direction = b - a
                if direction.length_squared < 1e-10:
                    continue
                t = max(0, min(1, (p - a).dot(direction) / direction.length_squared))
                distances.append((p - a - direction * t).length)
            return min(distances)

        xyz = [(p.x, p.y, eave + min(2.8, distance(p) * 0.72)) for p in coords]
        faces = [
            f
            for f in faces
            if inside(sum((coords[i] for i in f), Vector((0, 0))) / len(f), ring)
        ]
        roof = mesh(
            "Neighbor hipped roof " + str(neighbor["id"]),
            xyz,
            faces,
            tile if neighbor["id"] in [1448, 1423] else slate,
        )
        roof["evidence"] = "2025 DC aerial roof form; heights estimated"
        for a, b in zip(ring, ring[1:] + ring[:1]):
            line("Neighbor eaves and gutter", a, b, eave - 0.06, 0.13, 0.18, gutter)
        center = sum(ring, Vector((0, 0))) / len(ring)
        box(
            "Neighbor chimney",
            (center.x + 1.6, center.y - 1.3, eave + 2.4),
            (0.65, 0.85, 1.2),
            obj.data.materials[0],
        )
