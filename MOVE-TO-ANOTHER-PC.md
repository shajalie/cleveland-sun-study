# Windows GPU host: Moonlight or browser streaming

## Transfer to the RTX 5090 computer
1. Download the latest private GitHub release's cleveland-daylight-windows.zip and extract it completely.
2. Install Google Chrome once if it is absent.
3. Double-click START-DAYLIGHT.cmd. The local dashboard opens and verifies the actual NVIDIA GPU. No Tailscale installation, login or network setup is required for this step.

## Already using Moonlight
Open this computer's desktop through the existing Moonlight connection, launch START-DAYLIGHT.cmd and use the dashboard. Leave browser access off. Moonlight's existing setup provides the remote connection. This app does not install or configure Moonlight or Sunshine.

## Email-controlled website sharing
Open Connection options → Website sharing. Enter allowed emails and complete the one-time Cloudflare connection, then enable sharing. Send its dedicated HTTPS link to viewers. Their browsers sign in by email code; no phone app or Tailscale is needed. See WEBSITE-SHARING.md for setup and account permissions.

## Optional Tailscale browser access
In the PC dashboard, open Connection options and enable Web browser via Tailscale. Only this optional mode needs Tailscale installed and signed in on the computer and phone, on the same private network or an explicitly shared host. Tailscale may require a one-time HTTPS authorization. Setup failure leaves local/Moonlight rendering running.

Scan the website QR code or open Save this PC on the website on your phone once. The website stores that PC's private connection link only in that browser. Later visits to the original website open the saved PC stream automatically. Choose Change computer during the three-second countdown or add ?settings to the website URL to switch computers. Pairing can be repeated after clearing browser data. Disable browser access from the local dashboard to remove only this app's Tailscale Serve mapping; local/Moonlight use continues.

## What runs where
The published website is a small connection page. It does not load Three.js, the house model, HDR skies or a WebGL renderer. There is no automatic fallback to phone rendering if the computer is offline. The explicit Render on this device link opens the standalone GPU renderer at /render.html.

Browser streaming opens the chosen computer's private HTTPS page. That PC traces the light paths and sends JPEG frames; the phone sends scene controls. Moonlight streams the PC desktop using its own existing connection. One host session has one shared camera. Frame rate and image convergence depend on GPU, scene, connection and quality; 60 fps is not promised.

Keep the PC and renderer running. The launcher prevents Windows sleep while its host runs. STOP-DAYLIGHT.cmd stops this host and isolated browser. Tailscale is needed only while using its browser connection. Public Funnel is never enabled.

## Pairing and privacy
Connection links contain private pairing keys. Share them only with intended viewers. Browser profiles, credentials, pairing state and personal Tailscale configuration are excluded from GitHub and the ZIP. Each extracted copy generates a key. The hosted site stores a selected connection locally in the viewer's browser, never in the source or a server database. Stream controls require authentication. Network settings can only be changed through the authenticated loopback dashboard, including through Moonlight.

## Runtime and Blender
The release bundles Node, JavaScript dependencies, prebuilt assets, complete source and cleveland-daylight.blend with packed textures. Node, Python, Docker and Blender installations are unnecessary for the walkthrough.

For a Git clone, install Node 22.12+ and run npm ci and npm run build before START-DAYLIGHT.cmd. npm run dev serves the connection page; /render.html is the original renderer. npm test validates model assets. npm run test:remote checks the running stream. The optional older Docker bridge remains available with -UseDockerBridge; it is not the default.

The launcher applies High performance preferences and refuses integrated/unknown graphics for this NVIDIA package. Tested on RTX 2060 Max-Q; a physical RTX 5090 is not connected here. Open the packed scene in Blender 4.5 LTS or a compatible newer version to edit or rerender. README.md describes generation, Cycles validation and estimated house dimensions/materials. A faster GPU cannot remove those modeling uncertainties.
