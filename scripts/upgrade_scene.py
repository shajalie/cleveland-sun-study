"""Build the photo-informed scene. Geometry stages are independent of baking/hosting."""

import json
import random
import sys
from pathlib import Path
import bpy

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "scripts"))
from scene_build import (
    materials,
    geometry,
    site,
    vegetation,
    furniture,
    export,
    neighbors,
    surface_detail,
    roof_tiles,
)
from scene_build.architecture import (
    apply_photo_corrections,
    paint_exterior_joinery,
    add_arched_joinery,
)


def main():
    bpy.ops.wm.open_mainfile(filepath=str(P / "cleveland-daylight.blend"))
    data = json.loads((P / "model-data.json").read_text())
    output = P / "public"
    scene = bpy.context.scene
    scene.use_nodes = False
    context = dict(
        P=P,
        OUT=output,
        F=1200 / 3937,
        D=data,
        I=data["indoor"],
        O=data["outdoor"],
        rng=random.Random(301402),
        scene=scene,
        collision=json.loads((output / "collision.json").read_text()),
    )
    context.update(materials.build(OUT=context["OUT"]))
    context.update(
        geometry.build(
            I=context["I"], collision=context["collision"], scene=context["scene"]
        )
    )
    context.update(
        site.build(
            collision=context["collision"],
            F=context["F"],
            O=context["O"],
            box=context["box"],
            fence=context["fence"],
            iron=context["iron"],
            line=context["line"],
            remove_prefix=context["remove_prefix"],
            rod=context["rod"],
            roofwhite=context["roofwhite"],
            scene=context["scene"],
            slate=context["slate"],
            stone=context["stone"],
            terrace=context["terrace"],
            white=context["white"],
        )
    )
    apply_photo_corrections(
        data,
        context["box"],
        context["line"],
        context["white"],
        context["stone"],
        context["iron"],
        context["collision"],
    )
    add_arched_joinery(
        data, context["mesh"], context["rod"], context["white"], context["iron"]
    )
    paint_exterior_joinery(data, context["iron"])
    neighbors.build(
        data["outdoor"],
        context["mesh"],
        context["line"],
        context["box"],
        context["material"],
        context["inside"],
    )
    context.update(
        vegetation.build(
            F=context["F"],
            I=context["I"],
            O=context["O"],
            P=context["P"],
            bark=context["bark"],
            burgundy=context["burgundy"],
            collision=context["collision"],
            deciduous=context["deciduous"],
            green=context["green"],
            inside=context["inside"],
            mesh=context["mesh"],
            occupied=context["occupied"],
            pink=context["pink"],
            rng=context["rng"],
            rod=context["rod"],
            scene=context["scene"],
        )
    )
    context.update(
        furniture.build(
            collision=context["collision"],
            asset_templates=context["asset_templates"],
            bluecloth=context["bluecloth"],
            box=context["box"],
            iron=context["iron"],
            leather=context["leather"],
            linen=context["linen"],
            material=context["material"],
            mesh=context["mesh"],
            place_asset=context["place_asset"],
            remove_prefix=context["remove_prefix"],
            rod=context["rod"],
            scene=context["scene"],
            teak=context["teak"],
        )
    )
    grass_material = context["material"](
        "Mown grass blades", (0.045, 0.10, 0.018), 0.93
    )
    lawn = bpy.data.objects.get("Individual lawn blades")
    lawn.data.materials.clear()
    lawn.data.materials.append(grass_material)
    roof_tiles.build(context["mesh"])
    surface_detail.build(output)
    context.update(
        export.build(
            D=context["D"],
            OUT=context["OUT"],
            P=context["P"],
            RODS=context["RODS"],
            collision=context["collision"],
            mesh=context["mesh"],
            scene=context["scene"],
        )
    )


if __name__ == "__main__":
    main()
