"""Build a self-contained Windows host ZIP from committed source and verified dist.

Includes Node runtime and installed JS dependencies, but no browser profiles,
pairing keys, credentials, .git data, or personal tailnet state.
"""

from pathlib import Path
import subprocess, zipfile, json, hashlib, shutil, sys

P = Path(__file__).resolve().parents[1]
output = (
    Path(sys.argv[1]).resolve()
    if len(sys.argv) > 1
    else P.parent.parent / "cleveland-daylight-windows.zip"
)
node = Path(shutil.which("node") or "")
assert node.is_file(), "Node executable is required for the Windows portable package"
assert (P / "dist/index.html").is_file(), "Build the website first"
assert (P / "cleveland-daylight.blend").is_file(), "Packed scene is missing"
tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=P).decode().split("\0")
entries = {name: P / name for name in tracked if name and (P / name).is_file()}
for directory in ["dist", "node_modules"]:
    for f in (P / directory).rglob("*"):
        if f.is_file() and not f.is_symlink():
            entries[f.relative_to(P).as_posix()] = f
entries["cleveland-realism.blend"] = P / "cleveland-realism.blend"
entries["final-render.log"] = P / "final-render.log"
blender = P.parent.parent / "tools/blender-4.5.13-windows-x64"
assert (blender / "blender.exe").is_file(), "Bundled Blender runtime is required"
blender_release = json.loads((P / "remote/blender-release.json").read_text())
assert (
    hashlib.sha256((blender / "blender.exe").read_bytes()).hexdigest()
    == blender_release["installedExeSha256"]
)
for file in blender.rglob("*"):
    if file.is_file() and "__pycache__" not in file.parts:
        entries["runtime/blender/" + file.relative_to(blender).as_posix()] = file
entries["runtime/node.exe"] = node
entries["runtime/cloudflared.exe"] = P / "runtime/cloudflared.exe"
entries["runtime/CLOUDFLARED-LICENSE.txt"] = P / "remote/CLOUDFLARED-LICENSE.txt"
entries["runtime/LICENSE"] = P / "remote/NODE-LICENSE.txt"
connector = json.loads((P / "remote/cloudflared-release.json").read_text())
assert (
    hashlib.sha256(entries["runtime/cloudflared.exe"].read_bytes()).hexdigest()
    == connector["sha256"]
), "Cloudflare connector checksum mismatch"
for name in ["LICENSE", "LICENSE.txt"]:
    if (node.parent / name).is_file():
        entries["runtime/" + name] = node.parent / name
assert not any(
    ".runtime/" in n or "/.git/" in n or n.startswith(".env") for n in entries
)
with zipfile.ZipFile(
    output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
) as z:
    for name, file in sorted(entries.items()):
        z.write(file, "cleveland-daylight/" + name)
with zipfile.ZipFile(output) as z:
    assert z.testzip() is None
    names = set(z.namelist())
    for name in [
        "START-DAYLIGHT.cmd",
        "remote/server.mjs",
        "runtime/node.exe",
        "runtime/cloudflared.exe",
        "remote/sharing.mjs",
        "remote/sharing-auth.mjs",
        "remote/protect-secret.ps1",
        "node_modules/jose/package.json",
        "node_modules/puppeteer-core/package.json",
        "dist/index.html",
        "dist/render.html",
        "remote/configure-tailscale.ps1",
        "cleveland-daylight.blend",
        "cleveland-realism.blend",
        "realism-validation.json",
        "cycles-validation.json",
        "runtime/blender/blender.exe",
        "remote-validation.json",
    ]:
        assert "cleveland-daylight/" + name in names, name + " missing"
    assert not any("/.runtime/" in name for name in names)
report = {
    "file": output.name,
    "bytes": output.stat().st_size,
    "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    "sourceCommit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=P)
    .decode()
    .strip(),
    "files": len(names),
    "includesCredentials": False,
    "nodeVersion": subprocess.check_output([str(node), "--version"]).decode().strip(),
}
output.with_suffix(".manifest.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
