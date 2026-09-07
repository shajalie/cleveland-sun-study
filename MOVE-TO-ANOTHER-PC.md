# Move this project to another computer

## Fastest way to explore
Open https://cleveland-sun-study.sammyhajalie2g.chatgpt.site while signed into the same account. The new computer renders the scene locally; no file transfer is required. Check that the browser uses the dedicated GPU. On the original laptop, the Codex in-app browser reported integrated AMD Radeon graphics, while Blender Cycles used the NVIDIA RTX 2060 Max-Q.

## Edit or render in Blender
Open cleveland-daylight.blend in Blender 4.5 LTS or compatible newer Blender. Images are packed inside the file. Select a supported GPU rendering backend in Blender's system preferences and use Cycles GPU Compute. The scene and Python scripts remain editable; README.md documents reproduction and assumptions.

## Run the browser app locally
Install a Node.js version compatible with the package (20.19+ or 22.12+), open a terminal in this folder, then run:

    npm ci
    npm run dev

Open http://127.0.0.1:5173/. The source and shared assets are in app/ and public/.

## Run the prebuilt copy from the portable ZIP
The portable release also contains dist/. If Python 3 is installed, run from this folder:

    python -m http.server 5180 --bind 127.0.0.1 --directory dist

Open http://127.0.0.1:5180/. On Windows, py -3 can replace python. Serve the directory over HTTP; opening index.html directly is insufficient for the module and asset requests.

## Included
Editable packed Blender scene, application source, procedural scene/render scripts, HDR skies and textures, reference images, validation records, preserved original app, and setup notes. The portable ZIP additionally contains the compiled website and final Blender render log. Installed software, node_modules, credentials, and temporary render files are omitted.

The model remains an estimated reconstruction. A faster GPU improves convergence speed, not the accuracy of unmeasured geometry, glazing, trees or real-house brightness.
