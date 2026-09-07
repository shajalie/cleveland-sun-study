# One-click Windows GPU host

## Transfer to the RTX 5090 computer
1. Download the private GitHub release's cleveland-daylight-windows.zip and send that ZIP to the other computer, or download it there while signed into the authorized GitHub account.
2. Extract the ZIP completely. Do not run the launcher inside the compressed-folder preview.
3. Double-click START-DAYLIGHT.cmd. The launcher selects High performance for Edge/Chrome, starts an isolated NVIDIA render browser, checks the actual GPU, and opens a control page.
4. Choose Connect phone. Open its private link or scan its QR code on the phone.

The Windows host needs Microsoft Edge or Chrome and Tailscale. Install/sign into Tailscale on the host and phone once, using the same private network or an explicitly shared host. The release bundles Node and JavaScript dependencies; Node, Python, Docker and Blender installations are unnecessary for the walkthrough. Tailscale can require a one-time HTTPS authorization during initial setup.

Keep the computer, host process and Tailscale running. The launcher prevents Windows sleep while the render host runs. STOP-DAYLIGHT.cmd stops this host and its isolated browser. The launcher retains existing unrelated Tailscale mappings and uses an available private port. It never enables public Funnel access.

## What runs where
The host PC traces the light paths. The phone receives JPEG frames and sends only scene controls. It does not run the path tracer. Quality, navigation, seasonal skies, glazing, tree controls and the map operate on the host. One host session has one shared camera. Frame rate and image convergence depend on GPU, scene, connection and selected quality; this is not a promise of 60 fps.

The separately published Sites URL still renders directly on the device opening it. Use the launcher's private phone link when you want the desktop GPU to do the work.

The host verifies the actual WebGL GPU and refuses integrated/unknown graphics for this NVIDIA-targeted package. This was tested on the RTX 2060 Max-Q. An RTX 5090 has not been connected here; its GPU name is checked by the same launcher at startup. The launcher stores a backup of the prior browser GPU preference in .runtime/gpu-preference-before.json.

## Pairing and privacy
The connection link contains a private pairing key. Share it only with intended viewers. Pairing state, browser profiles, credentials and personal Tailscale state are excluded from the ZIP and GitHub. Each extracted copy generates its own key. Control APIs require authentication and same-origin requests; lost control connections release movement keys.

Native Windows Tailscale Serve is the portable default. The original Docker bridge integration is retained as an optional command: powershell -File remote/start.ps1 -UseDockerBridge. The default needs no Docker.

## Source checkout and Blender
For a Git clone, install compatible Node (20.19+ or 22.12+) and run npm ci before START-DAYLIGHT.cmd. npm run dev opens the original direct browser renderer. npm test checks model and reference assets. With the remote host running, node tests/remote-host.mjs checks the streaming/authentication/control path.

Open cleveland-daylight.blend in Blender 4.5 LTS or compatible newer Blender to edit or rerender. Textures are packed. README.md describes reproducible generation, Cycles rendering and daylight assumptions. A faster GPU improves computation; unmeasured dimensions, glass and trees remain accuracy limits.

Technical references: https://pptr.dev/api/puppeteer.launchoptions ; https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/gpu/config/gpu_switches.cc ; https://tailscale.com/docs/reference/tailscale-cli/serve
