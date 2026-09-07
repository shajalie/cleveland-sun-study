# Cleveland Daylight

Interactive daylight reconstruction of 3014 Cleveland Avenue NW. Both floors and the property share an enclosed meter-scale scene. The browser traces the same geometry, textures and HDR lighting as Blender Cycles.

## Remote desktop GPU and phone

Use the private GitHub portable release and START-DAYLIGHT.cmd. It opens a local NVIDIA GPU dashboard with no Tailscale requirement. Use the dashboard through existing Moonlight, or enable optional Web browser via Tailscale in Connection options. Its website pairing link remembers the chosen computer on the phone. The published Sites root is now a lightweight connection launcher and never automatically loads the path tracer. See MOVE-TO-ANOTHER-PC.md for both connection modes, pairing, startup and shutdown.

## Run

Requires Node 20.19+ or 22.12+. Run npm ci, then npm run dev. Open http://127.0.0.1:5173/ for the connection page or /render.html for explicit rendering on this device. npm run build writes dist. The existing owner-private Site identity remains in .openai/hosting.json.

Drag to look, tap floor/ground to teleport, use WASD/arrows or the touch pad. Floor buttons, labeled maps and shortcuts cover indoors and outdoors. Orbit retains all roof and ceiling obstructions. Four seasonal dates and three local times provide 12 atmospheric skies without interpolation. Local time uses America/New_York DST rules.

Explore uses reduced resolution and up to 512 samples. Fine detail uses full resolution and up to 2048. Pause to let noise converge. The initial still is labeled as a Cycles reference; interacting enters the live renderer. Comparisons require 128 samples. Exposure stays fixed.

## Reproduce

Blender 4.5.13 LTS portable was installed from the official Blender release archive at ../../tools/blender-4.5.13-windows-x64/blender.exe. OptiX rendering was verified on this PC's RTX 2060 Max-Q. Python dependencies: numpy, pillow, pandas, pvlib and tzdata; requests is only needed for optional evidence retrieval.

Run, in this order:

1. python scripts/textures.py
2. node scripts/scenarios.mjs
3. blender --background --python scripts/scene.py
4. blender --background --python scripts/bake_skies.py
5. blender --background --python scripts/render.py
6. python scripts/validate.py
7. npm test
8. npm run build

Use the installed Blender executable path in place of blender. The scene generator writes cleveland-daylight.blend, public/house.glb, public/model.json and collision data. The editable blend has packed images. Reference rendering removes prior generated lights/test objects before rerunning. Cycles uses 512 samples, denoising, 20 total / 12 diffuse / 16 transmission / 24 transparent bounce limits; browser uses 20 bounces and multiple importance sampling.

## Lighting and validation

Nishita skies use air/dust/ozone densities of 1, an estimated 90 m altitude and a 0.53° sun disk. Sky rendering is 4096 × 2048 at four samples, area-averaged to shared 2048 × 1024 HDR maps. Solar disk alignment is checked against the intended world-space vector. Appearance uses no extra Sun. The separate direct-shadow diagnostic uses a normalized directional source.

Overcast uses the CIE zenith-bright shape and 35% of clear horizontal illumination: an explicit weather assumption. Both engines use the global HDR scale 1/30 and display curve sRGB(E L / (1 + E L)), E = 8 at default +3 EV. There is no room-dependent gain, adaptive exposure or ambient fill. EV labels are relative display settings, not EV100 calibration. Pixel values are never labeled lux.

Glass uses IOR 1.5 and estimated normal transmission. Camera paths refract/reflect. Cycles uses straight attenuated shadow paths through thin architectural glass to avoid noisy refractive caustic sampling; this is an intentional approximation and differs from the browser BSDF. The 12% covering is attenuation only, not curtain scattering. Pool water uses IOR 1.333; underwater caustics are unvalidated. Foliage is explicit leaf/branch geometry with approximate rough transmission, not a measured leaf BSDF.

See public/validation.html for methods, sources and assumptions. validation-results.json contains independent NREL SPA checks via pvlib for 18 positions including DST transitions, and paired Cycles image checks for sealed-room leakage, indirect bounce contribution, reduced transmission and reduced reflectance. Display pixel statistics are not lux. Browser and Cycles matching views were visually inspected; navigation was tested interactively.

## Reconstruction limits

Indoor coordinates are meters; outdoor US survey feet convert once by 1200/3937. Stored orientation vectors are retained. Blender coordinates are (x, plan_y, height); Three/glTF are (x, height, -plan_y).

Additional Compass listing photos informed broad sunroom glazing, arched landing/powder windows, joinery, furnishings and terrace levels. These remain estimates. Photos cannot calibrate brightness because exposure/editing and electric lighting are unknown. Trees, glass products, roofs and neighbor heights remain major uncertainties. Tree crowns and glazing are adjustable. Winter retains leaf-on foliage. Terrain is simplified; basement and physical stair flight are omitted.

The supplied ZIP is untouched outside the project. legacy/, src/, export HTML and the original Python builder preserve the old app. Use npm build for the new app.

Sources: supplied plans/photos; https://www.compass.com/homedetails/3014-Cleveland-Ave-NW-Washington-DC-20008/1UXTV4_pid/ ; https://docs.blender.org/manual/en/4.5/render/shader_nodes/textures/sky.html ; https://github.com/gkjohnson/three-gpu-pathtracer ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.solarposition.get_solarposition.html

An exploratory reconstruction, not a calibrated illuminance model or certified building assessment.

The Leaf-off bound removes leaves while retaining branches/trunks; it is a sensitivity bound, not a verified winter species model.

The registered project footprint was retained. Its room dimensions remain approximate: for example, the modeled living-room depth is about 8.4 m, while the listing plan labels 25 ft (7.62 m). This roughly 10% difference is an unresolved geometry uncertainty and affects daylight penetration.
Estimated tree leaves and branches are trimmed against the building envelope. The browser repeats leaf trimming after crown-size changes.
