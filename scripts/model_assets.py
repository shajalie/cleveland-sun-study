"""Download redistributable CC0 models via the Poly Haven API, with checksums."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests, hashlib, json

P = Path(__file__).resolve().parents[1]
OUT = P / ".runtime/model-assets"
OUT.mkdir(parents=True, exist_ok=True)
records = []
for asset in ["fir_tree_01", "tree_small_02", "chinese_armchair"]:
    r = requests.get("https://api.polyhaven.com/files/" + asset, timeout=40)
    r.raise_for_status()
    info = r.json()["gltf"]["1k"]["gltf"]
    folder = OUT / asset
    folder.mkdir(exist_ok=True)
    items = {asset + "_1k.gltf": info, **info.get("include", {})}

    def download(item):
        name, entry = item
        dest = folder / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if (
            not dest.exists()
            or hashlib.md5(dest.read_bytes()).hexdigest() != entry["md5"]
        ):
            r = requests.get(entry["url"], timeout=180)
            r.raise_for_status()
            dest.write_bytes(r.content)
        raw = dest.read_bytes()
        assert hashlib.md5(raw).hexdigest() == entry["md5"], name
        return {
            "file": asset + "/" + name,
            "url": entry["url"],
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

    with ThreadPoolExecutor(max_workers=5) as pool:
        files = list(pool.map(download, items.items()))
    records.append(
        {
            "asset": asset,
            "license": "CC0",
            "source": "https://polyhaven.com/a/" + asset,
            "files": files,
        }
    )
    print("MODEL_DOWNLOADED", asset, flush=True)
(P / "public/textures/model-sources.json").write_text(json.dumps(records, indent=2))
