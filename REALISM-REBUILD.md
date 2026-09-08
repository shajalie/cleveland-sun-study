# Photo-based model and precomputed daylight

The v1.2 house is a useful coordinate and navigation foundation, but its sparse,
procedural surfaces and foliage are visibly unlike the listing. The rebuild uses
listing photos 0–55 and the official March 27, 2025 DC aerial image. Images 56 onward on the listing
page are other properties, and are excluded as evidence for this house.

## Rendering decision

Precomputed diffuse light transport is appropriate for a static house. A lightmap
stores light on surfaces, not a fixed camera image, so the user can walk freely.
The initial set is March 20, June 21, September 22 and December 21, each at 9 AM,
1 PM and 5 PM local time, plus an overcast counterpart. No interpolation is claimed.
Diffuse transport is baked with Cycles on the RTX 2060. Glass and reflections stay
view dependent; the live ray tracer remains available for material sensitivity.

Unreal Lightmass supports this same precomputed approach. Unreal is a viable later
runtime, but changing engines does not reconstruct missing fences, landscaping or
furniture. Lumen would again spend GPU time recomputing dynamic lighting. The first
implementation therefore tests baked transport in the existing renderer and keeps
the already working email-protected phone stream.

## Evidence and estimates

The 2025 DC orthophoto was retrieved again from the official DC GIS service at its
0.08 m ground pixel spacing. The 2000 × 2000 export covers 160 × 160 m. The parcel
is registered using its EPSG:26985 coordinates, with local origin
(394789.9419064714, 139670.6757774111). `scripts/fetch_aerial.py` records the request,
extent and SHA-256; `scripts/audit_reference.py` overlays the supplied geometry.
This confirms the overall placement and exposes differences around the rear wings.
Roof overhangs and off-nadir displacement prevent interpreting every roof pixel as
a ground-level wall measurement.

The Compass and Redfin floor-plan images both resolve to 630 × 394 pixels. The
printed room dimensions and traced diagram do not consistently agree. The model
retains the geographically registered envelope; it does not silently rescale the
whole house to fit one ambiguous room label.

- Privacy fence: dark vertical boards and top rails, visible in photos 45–52.
  Boundary alignment follows the supplied parcel; the 1.9 m height is estimated.
- Neighbor footprints: retained from the supplied geospatial data, with pitched
  roofs constrained to those outlines. Eaves at 6.5 m and ridge rises up to 2.8 m
  are estimates, as are regular window openings and facade finishes.
- Vegetation: evergreen versus deciduous silhouettes inferred from photos and the
  aerial. Species, exact leaf-area density and crown heights remain estimates.
  Evergreen foliage remains present in winter; deciduous foliage changes by season.
- Exterior: white rear roof surfaces, terracotta main hip, stucco retaining walls,
  terrace railings, blue umbrella and pool loungers are based on photos and aerial.
  Photos 0–4 and 54 inform the deeper porch, square columns, dentil cornice and
  balcony parapet. Photos 51–52 inform narrower rear windows and the dining-table
  placement. Arched sash and exterior dark window faces are modeled separately.
- Interior: floor plans retained; leather sofa, linen curtains, joinery, framing and
  furnishings reconstructed approximately from the listing images.
- Surface maps: scanned CC0 Poly Haven materials, with source URLs and hashes in
  public/textures/scanned/sources.json. These reproduce material classes, not exact
  measured reflectance or the specific wood and stone used at this address.

Realistic appearance does not establish measured lighting accuracy. Glazing,
vegetation density and neighboring heights remain consequential uncertainties.
The garden's vertical grading and the lower-level rooms are not reconstructed
from measured elevation data. These remain limitations, rather than validated
matches to the photographs.

## Code organization

`scripts/upgrade_scene.py` orchestrates independently callable build stages under
`scripts/scene_build/`: materials, geometry, site, architecture, neighbors,
vegetation, furniture and export. Lighting baking and denoising are separate from
scene construction. The browser separates navigation, scene loading, baked
lighting and solar calculations. `remote/` owns streaming and sharing.

`tests/navigation.mjs` checks room reachability, floor heights, walls, pool and
fence barriers. The build lint checks undefined names and imports; generated
geometry is verified through actual Blender builds and inspection renders.

## Technical references

- https://dev.epicgames.com/documentation/en-us/unreal-engine/precomputed-lighting-scenarios
- https://dev.epicgames.com/documentation/en-us/unreal-engine/cpu-lightmass-global-illumination-in-unreal-engine
- https://docs.blender.org/manual/en/latest/render/cycles/baking.html
- https://polyhaven.com/license

Validation results and practical bake timing will be recorded after the actual
renders and interactive viewer checks, rather than inferred from source changes.

## Surface detail and streamed Cycles refinement

The detailed material pass uses 2048-pixel diffuse, roughness and tangent normal
maps with meter-scale UVs. Separate UVs retain surface detail when lightmaps are
added. Leather, fabric, plaster, wood, stone and painted fence surfaces have
individual material responses. Roof tile geometry supplies the profile and
row shadows; a grain texture avoids painting a second tile grid over it.

`remote/cycles-renderer.mjs` owns a private Blender child process. The worker
accepts validated camera and scenario data over stdin, uses OptiX at 128 samples,
and returns complete JPEG files atomically. It exposes no network listener.
The protected host streams precomputed navigation, requests native detail after
a short pause, and cancels an active detail render when the camera moves.
Cache keys include the scene version and all view parameters. Two hundred
completed views are retained on disk; private runtime state stays out of releases.

Native stationary rendering preserves view-dependent reflection and small surface
normal detail that diffuse lightmaps alone cannot reproduce. It still uses the
same estimated geometry and materials. More samples cannot correct the unresolved
floor-plan dimensions, garden grading or missing lower level.
