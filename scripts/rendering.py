"""Shared architectural glass transport for Cycles previews, bakes and streaming."""

import math
import bpy
import numpy as np


def configure_sky(scene, case, kind, root):
    """Use the identical HDR or CIE sky for the bake, references and live worker."""
    if kind not in {"clear", "overcast"}:
        raise ValueError("Unknown sky")
    nodes, links = scene.world.node_tree.nodes, scene.world.node_tree.links
    nodes.clear()
    env = nodes.new("ShaderNodeTexEnvironment")
    if kind == "clear":
        image = bpy.data.images.load(
            str(root / "public" / case["hdr"].lstrip("/")), check_existing=True
        )
    else:
        image = bpy.data.images.get("Shared overcast sky") or bpy.data.images.new(
            "Shared overcast sky", width=256, height=128, float_buffer=True
        )
        pixels = np.ones((128, 256, 4), np.float32)
        for y in range(128):
            up = math.cos((1 - y / 128) * math.pi)
            pixels[y, :, :3] = (
                case["overcast_zenith"] * (1 + 2 * up) / 3 if up > 0 else 0
            )
        image.pixels.foreach_set(pixels.ravel())
        image.update()
    env.image = image
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 1
    output = nodes.new("ShaderNodeOutputWorld")
    links.new(env.outputs[0], background.inputs[0])
    links.new(background.outputs[0], output.inputs[0])


def configure_glass(transmission=0.82):
    """Thin parallel panes: attenuated straight shadow rays, dielectric camera rays.

    Each pane has two faces. The square root gives the specified normal-incidence
    transmission after both faces. This avoids undersampled refractive sun caustics;
    it is an architectural approximation, not a measurement of these windows.
    """
    for material in bpy.data.materials:
        if not material.name.startswith("Glazing"):
            continue
        nodes, links = material.node_tree.nodes, material.node_tree.links
        shader = nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = (
            *([math.sqrt(transmission / (0.96 * 0.96))] * 3),
            1,
        )
        shadow = nodes.get("Architectural shadow") or nodes.new(
            "ShaderNodeBsdfTransparent"
        )
        shadow.name = "Architectural shadow"
        shadow.inputs[0].default_value = (*([math.sqrt(transmission)] * 3), 1)
        paths = next((n for n in nodes if n.type == "LIGHT_PATH"), None) or nodes.new(
            "ShaderNodeLightPath"
        )
        mix = next((n for n in nodes if n.type == "MIX_SHADER"), None) or nodes.new(
            "ShaderNodeMixShader"
        )
        links.new(paths.outputs["Is Shadow Ray"], mix.inputs[0])
        links.new(shader.outputs[0], mix.inputs[1])
        links.new(shadow.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], nodes.get("Material Output").inputs["Surface"])
