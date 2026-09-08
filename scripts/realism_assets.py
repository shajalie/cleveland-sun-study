"""Retrieve CC0 scanned surface maps and recover the supplied aerial reference."""

from pathlib import Path
import requests, json, re, base64, hashlib
from concurrent.futures import ThreadPoolExecutor

P = Path(__file__).resolve().parents[1]
OUT = P / "public/textures/scanned"
OUT.mkdir(parents=True, exist_ok=True)
assets = [
    "wood_floor",
    "plastered_wall_02",
    "aerial_grass_rock",
    "clay_roof_tiles",
    "brown_brick_02",
    "bark_brown_02",
    "fabric_pattern_05",
    "rocky_terrain_02",
    "terracotta_floor_tiles",
]
records = []


def download(asset):
    r = requests.get("https://api.polyhaven.com/files/" + asset, timeout=40)
    r.raise_for_status()
    data = r.json()
    files = {}
    for channel in ["diff", "nor_gl", "rough"]:
        formats = data.get(
            {"diff": "Diffuse", "rough": "Rough"}.get(channel, channel), {}
        ).get("1k", {})
        info = formats.get("jpg") or formats.get("png")
        if not info:
            continue
        url = info["url"]
        dest = OUT / (asset + "_" + channel + Path(url).suffix)
        if not dest.exists():
            r = requests.get(url, timeout=90)
            r.raise_for_status()
            dest.write_bytes(r.content)
        files[channel] = {
            "file": dest.name,
            "url": url,
            "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        }
    return {
        "asset": asset,
        "source": "https://polyhaven.com/a/" + asset,
        "license": "CC0",
        "files": files,
    }


with ThreadPoolExecutor(max_workers=4) as pool:
    for record in pool.map(download, assets):
        records.append(record)
        print("SURFACE_READY", record["asset"], list(record["files"]), flush=True)
(OUT / "sources.json").write_text(json.dumps(records, indent=2))
html = (P / "src/outdoor.html").read_text(encoding="utf8")
for i, m in enumerate(
    re.finditer(r"data:image/(jpeg|png);base64,([A-Za-z0-9+/=\r\n]+)", html)
):
    dest = (
        P
        / "evidence"
        / ("supplied-aerial-" + str(i) + (".jpg" if m[1] == "jpeg" else ".png"))
    )
    dest.write_bytes(base64.b64decode(m[2]))
    print("AERIAL_READY", dest.name)
