"""Retrieve georeferenced official DC imagery; preserve its native spatial scale."""

import hashlib
import json
from pathlib import Path

import requests
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
SERVICE = "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/DC_Aerial_Photo/MapServer"


def fetch_aerial():
    output = ROOT / "evidence" / "aerial-2025"
    output.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    metadata = session.get(f"{SERVICE}/0", params={"f": "json"}, timeout=60).json()
    x, y = Transformer.from_crs(4326, 26985, always_xy=True).transform(
        -77.06033745, 38.92485352
    )
    # 160 m across at 0.08 m per pixel: house and surrounding shade obstructions.
    bounds = [x - 80, y - 80, x + 80, y + 80]
    params = {
        "f": "json",
        "bbox": ",".join(map(str, bounds)),
        "bboxSR": 26985,
        "imageSR": 26985,
        "size": "2000,2000",
        "format": "png32",
        "transparent": "false",
        "layers": "show:0",
    }
    response = session.get(f"{SERVICE}/export", params=params, timeout=120)
    response.raise_for_status()
    export = response.json()
    if "error" in export:
        raise RuntimeError(export["error"])
    image = session.get(export["href"], timeout=120)
    image.raise_for_status()
    (output / "neighborhood.png").write_bytes(image.content)
    record = {
        "source": SERVICE,
        "layer": metadata,
        "request": params,
        "extent": export["extent"],
        "width": export["width"],
        "height": export["height"],
        "sha256": hashlib.sha256(image.content).hexdigest(),
    }
    (output / "source.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "file": str(output / "neighborhood.png"),
                "extent": export["extent"],
                "description": metadata.get("description"),
            }
        )
    )


if __name__ == "__main__":
    fetch_aerial()
