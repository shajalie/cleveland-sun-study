"""Curved, overlapping terracotta tiles; surface relief remains real geometry."""

import math
import bpy


def build(mesh):
    roof = bpy.data.objects.get("Hip roof")
    if roof is None:
        raise RuntimeError("Main hip roof is missing")
    vertices = []
    faces = []
    material_indices = []
    clay = roof.data.materials[0].copy()
    clay.name = "Modeled terracotta clay"
    nodes = clay.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    for node in list(nodes):
        if node.type not in {"BSDF_PRINCIPLED", "OUTPUT_MATERIAL"}:
            nodes.remove(node)
    shader.inputs["Base Color"].default_value = (0.31, 0.115, 0.054, 1)
    shader.inputs["Roughness"].default_value = 0.78
    roof.data.materials[0] = clay
    for surface in roof.data.polygons[:4]:
        corners = [
            roof.matrix_world @ roof.data.vertices[i].co for i in surface.vertices
        ]
        eave_a, eave_b, ridge_b, ridge_a = corners
        across = (eave_b - eave_a).normalized()
        slope = ((ridge_a + ridge_b) - (eave_a + eave_b)) / 2
        count_up = max(1, math.ceil(slope.length / 0.30))
        normal = across.cross(slope).normalized()
        if normal.z < 0:
            normal = -normal
        for row in range(count_up):
            t0 = row / count_up
            t1 = min(1, (row + 1.16) / count_up)
            left = eave_a.lerp(ridge_a, t0)
            right = eave_b.lerp(ridge_b, t0)
            left_top = eave_a.lerp(ridge_a, t1)
            right_top = eave_b.lerp(ridge_b, t1)
            # Anchor columns to the eave. Re-dividing each narrower row would
            # skew every tile toward the hip and produce implausible zigzags.
            bottom_left = (left - eave_a).dot(across)
            top_left = (left_top - eave_a).dot(across)
            bottom_right = (right - eave_a).dot(across)
            top_right = (right_top - eave_a).dot(across)
            first = math.floor(max(bottom_left, top_left) / 0.205)
            last = math.ceil(min(bottom_right, top_right) / 0.205)
            for column in range(first, last):
                low = max(column * 0.205, bottom_left, top_left)
                high = min((column + 1) * 0.205, bottom_right, top_right)
                if high - low < 0.005:
                    continue
                start = len(vertices)
                for edge in range(2):
                    for j in range(9):
                        distance = low + (high - low) * j / 8
                        u = (distance - column * 0.205) / 0.205
                        position = (left if edge == 0 else left_top) + across * (
                            distance - (bottom_left if edge == 0 else top_left)
                        )
                        position += normal * (
                            0.015 + (1 - edge) * 0.018 + math.sin(u * math.pi) * 0.045
                        )
                        vertices.append(position)
                for j in range(8):
                    faces.append(
                        (start + j, start + j + 1, start + j + 10, start + j + 9)
                    )
                # The visible lip gives each row a shadow and a thin tile edge.
                lip = len(vertices)
                for j in range(9):
                    vertices.append(vertices[start + j] - normal * 0.012)
                for j in range(8):
                    faces.append((start + j, lip + j, lip + j + 1, start + j + 1))
                material_indices.extend([(row * 17 + column * 7) % 5] * 16)
    obj = mesh(
        "Individual curved terracotta roof tiles",
        vertices,
        faces,
        clay,
    )
    for i, factor in enumerate([0.91, 0.96, 1.04, 1.09]):
        variant = clay.copy()
        variant.name = f"Modeled terracotta clay variation {i}"
        variant.node_tree.nodes.get("Principled BSDF").inputs[
            "Base Color"
        ].default_value = (0.31 * factor, 0.115 * factor, 0.054 * factor, 1)
        obj.data.materials.append(variant)
    for poly, index in zip(obj.data.polygons, material_indices):
        poly.material_index = index
        poly.use_smooth = poly.index % 16 < 8
    obj["roof_tiles"] = True
    obj["evidence"] = (
        "Barrel-tile form visible in Compass photo 54 and 2025 DC aerial; tile size inferred"
    )
    print("ROOF_TILE_RELIEF_READY", len(vertices), len(faces), flush=True)
