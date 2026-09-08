# Saved checkpoint — September 7, 2026

This version is preserved before exploring a different rendering approach. The
working simulator remains available; changing repository visibility does not
change the website's email allowlist or publish any local connection credentials.

## Restore or reuse the work

- Source and history: this repository. The `saved-before-next-approach-2026-09-07`
  tag identifies this checkpoint.
- [Version 2.0.0 downloads](https://github.com/shajalie/cleveland-sun-study/releases/tag/v2.0.0):
  `cleveland-daylight-windows.zip` contains the runnable Windows application,
  bundled Blender and Node, final editable `cleveland-realism.blend`, original
  `cleveland-daylight.blend`, textures, baked lighting, and source at release time.
- `cleveland-reconstruction-inputs.zip` in the same release preserves reference
  images, the 2025 aerial and registration data, raw CC0 model inputs, prepared
  model library, and `cleveland-bake.blend`. Follow its `RESTORE-INPUTS.txt` to
  restore the existing build pipeline. Both archives have SHA-256 manifests.
- Validation reports in the release cover the original workspace and a fresh
  extraction using its bundled runtime on the RTX 2060 Max-Q.

The original workspace, raw downloaded listing HTML, intermediate work, and local
account configuration remain saved on the original PC. Browser profiles,
credentials, process state, caches, and obsolete exports are intentionally absent
from downloadable archives. A different computer configures its own sharing.

## What this version does

There are 24 precomputed daylight scenarios, free camera navigation, and native
Cycles refinement while stationary. The phone receives images and sends controls.
An uncached detailed view took approximately 19–21 seconds on the tested laptop.
Six detailed views are bundled, and finished views are cached.

See `README.md` for build commands and `REALISM-REBUILD.md` for provenance and
limitations. Some floor-plan dimensions, garden grading, neighboring heights,
foliage and material properties are estimates. The lower level is incomplete.
Changing renderers cannot by itself resolve those geometry uncertainties.

## Credential review before public visibility

The review covers all Git branches and tags, all four existing Windows release
archives, supplemental reconstruction inputs, and GitHub release/issue/comment
metadata. Gitleaks scans text and full Git history. An additional scan checks
binary contents against the actual local connection credentials and checks
archives for private runtime files. Reports contain locations and counts only;
credential values are never included. The release includes a redacted audit
summary. No GitHub Actions runs or artifacts existed at review time.

Keep `.runtime/`, `runtime/`, `.env*`, browser profiles, tokens and private keys out
of Git. A clean scan is evidence for this checkpoint, not a guarantee about future
changes.
