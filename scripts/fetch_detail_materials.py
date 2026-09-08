"""Restore the pinned CC0 material files from their checked-in source records."""

import hashlib
import json
import argparse
from pathlib import Path
import requests


def main():
    directory = Path(__file__).resolve().parents[1] / "public/textures/detail"
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", action="append", default=[])
    arguments = parser.parse_args()
    for asset in arguments.asset:
        if not asset.replace("_", "").isalnum():
            raise ValueError("Invalid material identifier")
        info = requests.get(
            "https://api.polyhaven.com/info/" + asset, timeout=60
        ).json()
        files = requests.get(
            "https://api.polyhaven.com/files/" + asset, timeout=60
        ).json()
        record = {
            "asset": asset,
            "license": "CC0",
            "source": "https://polyhaven.com/a/" + asset,
            "dimensionsMillimeters": info.get("dimensions"),
            "files": {},
        }
        for channel, key in [
            ("diff", "Diffuse"),
            ("normal", "nor_gl"),
            ("rough", "Rough"),
            ("height", "Displacement"),
        ]:
            formats = files.get(key, {}).get("2k", {})
            item = (
                formats.get("png")
                if channel == "height"
                else formats.get("jpg") or formats.get("png")
            )
            if not item:
                continue
            response = requests.get(item["url"], timeout=120)
            response.raise_for_status()
            filename = asset + "_" + channel + Path(item["url"]).suffix
            (directory / filename).write_bytes(response.content)
            record["files"][channel] = {
                "file": filename,
                "url": item["url"],
                "sha256": hashlib.sha256(response.content).hexdigest(),
            }
        (directory / (asset + ".json")).write_text(json.dumps(record, indent=2) + "\n")
    for record_path in sorted(directory.glob("*.json")):
        record = json.loads(record_path.read_text())
        for item in record["files"].values():
            target = directory / item["file"]
            if (
                target.exists()
                and hashlib.sha256(target.read_bytes()).hexdigest() == item["sha256"]
            ):
                continue
            response = requests.get(item["url"], timeout=120)
            response.raise_for_status()
            if hashlib.sha256(response.content).hexdigest() != item["sha256"]:
                raise RuntimeError("Material checksum changed: " + item["file"])
            target.write_bytes(response.content)
        print("MATERIAL_VERIFIED", record["asset"], flush=True)


if __name__ == "__main__":
    main()
