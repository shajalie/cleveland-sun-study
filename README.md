# Cleveland Daylight

A photo-informed reconstruction of 3014 Cleveland Avenue NW, Washington DC. The default tour reuses precomputed daylight while allowing free camera movement. The laptop draws the scene; a phone receives images and sends controls.

## Open on a PC or phone

Download the [Windows release ZIP](https://github.com/shajalie/cleveland-sun-study/releases/tag/v2.0.0), extract it, and double-click **START-DAYLIGHT.cmd**. Chrome and an NVIDIA GPU driver are required. Node and Blender are bundled; **no separate Blender installation is needed.** See [SAVED-CHECKPOINT.md](SAVED-CHECKPOINT.md) for the reconstruction inputs and restore instructions.

The dashboard offers email-controlled Website sharing, optional Tailscale, and use through existing Moonlight. See WEBSITE-SHARING.md and MOVE-TO-ANOTHER-PC.md. The existing Sites address is a lightweight connection launcher; its separate build excludes the 3D payload entirely. Use npm run build:site only for that website; npm run build creates the full Windows host assets.

## Explore and compare

Drag to look, use WASD/arrows or touch controls, and tap visible floor/ground or the map to move. Floor buttons bridge the two levels. Orbit keeps the house roofs and neighboring obstructions visible.

Four dates (March 20, June 21, September 22, December 21), three local times (9 AM, 1 PM, 5 PM), and clear/overcast skies provide **24 lighting scenarios**. There is no time interpolation. Time follows America/New_York, including daylight saving time.

Baked daylight makes movement responsive. After the camera rests for 1.2 seconds, the PC renders a detailed 128-sample view in native Blender Cycles and streams that image. Moving returns immediately to the preview and cancels an unfinished detail render. Six finished Cycles views are bundled, including the initial viewpoint. Other completed views are cached, so revisiting the same view is immediate. The disk cache retains 200 views. The phone decodes JPEG images and sends controls; it does not load the 3D scene. Exposure remains fixed while walking. March and December use an estimated deciduous leaf-off state; evergreen foliage remains. These are seasonal assumptions, not a botanical survey.

## Rebuild the scene and lighting

The portable release includes the editable, texture-packed **cleveland-realism.blend**. The original **cleveland-daylight.blend** is retained as the source-plan foundation. Blender 4.5.13 LTS was used with OptiX on this laptop's RTX 2060 Max-Q.

From a source checkout with Node dependencies installed, run:

1. `python scripts/realism_assets.py`, `python scripts/model_assets.py`, and `python scripts/fetch_detail_materials.py` (requires requests).
2. `blender -b --python-exit-code 1 --python scripts/prepare_models.py`
3. `blender -b --python-exit-code 1 --python scripts/upgrade_scene.py`
4. `blender -b --python-exit-code 1 --python scripts/bake_daylight.py -- --prepare`
5. `blender -b --python-exit-code 1 --python scripts/bake_daylight.py -- --overcast`
6. `node scripts/compress_scene.mjs`
7. `blender -b --python-exit-code 1 --python scripts/reference_realism.py`
8. `npm test`, `npm run test:baked`, and `npm run build`.

Use the full path to Blender if it is not on PATH. Geometry is authored in Blender coordinates (x, plan_y, height); glTF uses (x, height, -plan_y). Indoor meters and the outdoor US survey-foot conversion 1200/3937 are retained. Scene chunks have checksums and stay below the hosting per-file limit.

## Lighting and limits

Cycles bakes direct and indirect diffuse light without the surface color, using 96 samples, up to 16 total and 10 diffuse bounces, then HDR denoising. A second UV set stores the lightmaps. Two local indoor reflection probes accompany each scenario. The tour combines those with surface textures and view-dependent reflection/transmission approximations. **The baked tour is not full live path tracing.**

Clear skies use the existing Nishita atmosphere and 0.53-degree solar disk. Overcast follows a CIE distribution at an assumed 35% of clear horizontal illumination. The shared HDR scale is 1/30. The rebuilt display uses AgX and relative fixed exposure, normally +3 EV. Architectural panes use an 82% thin-glass shadow approximation with dielectric camera/reflection paths. It is not calibrated EV100, and pixels are not lux. Blender and browser AgX contrast differ slightly.

The fence, terrace finishes, rear roof surfaces, furnishings, grass blades and foliage were revised against listing photos 0-55 and the March 27, 2025 DC aerial. 2048-pixel scanned material maps add physically scaled plaster grain, leather pores, fabric weave, wood grain and stone wear. Main roof tiles have curved geometry, overlap and separate lips. Scanned surface and tree models are CC0 Poly Haven assets; source URLs and hashes are included in public/textures. Neighbor footprints are retained, while facade details and heights remain estimates. Trees are trimmed where they would intersect the house.

This remains a reconstruction, not a measured replica. The supplied plan's living-room depth is about 8.4 m versus the listing's 25 ft (7.62 m), an unresolved roughly 10% discrepancy. Window dimensions/transmission, material reflectance, tree species/density and neighbor heights remain consequential uncertainties. The basement and a physical stair flight are omitted. Photographs cannot establish actual brightness because exposure, editing and electric lighting are unknown.

See REALISM-REBUILD.md, realism-validation.json and public/validation.html. Original sky/transport diagnostics remain in validation-results.json; they do not independently validate the rebuilt geometry. The actual RTX 5090 is not connected to this workspace.
