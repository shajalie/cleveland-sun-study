"""Make a spatially registered aerial/model comparison, without changing the model."""

import base64
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = json.loads((ROOT / "model-data.json").read_text())
    outdoor = data["outdoor"]
    directory = ROOT / "evidence/aerial-2025"
    extent = json.loads((directory / "source.json").read_text())["extent"]
    parcel = json.loads((directory / "parcel.json").read_text())["features"][0][
        "geometry"
    ]["rings"][0]
    origin = parcel[7]

    def pixel(x, y):
        east = origin[0] + outdoor["ux"][0] * x + outdoor["uy"][0] * y
        north = origin[1] + outdoor["ux"][1] * x + outdoor["uy"][1] * y
        return ((east - extent["xmin"]) / 0.08, (extent["ymax"] - north) / 0.08)

    def polygon(points, color, label):
        coords = " ".join(
            f"{x:.2f},{y:.2f}" for x, y in map(lambda p: pixel(*p), points)
        )
        return f'<polygon points="{coords}" fill="none" stroke="{color}" stroke-width="2"><title>{html.escape(label)}</title></polygon>'

    overlays = polygon(
        [[x * 1200 / 3937, y * 1200 / 3937] for x, y in outdoor["parcel"]],
        "#00fffa",
        "GIS parcel",
    )
    overlays += polygon(
        data["indoor"]["floors"][0]["outline"], "#ffff00", "Current main floor"
    )
    overlays += polygon(
        [[x * 1200 / 3937, y * 1200 / 3937] for x, y in outdoor["outline"]],
        "#ff44ff",
        "GIS building outline",
    )
    for neighbor in outdoor["neighbors"]:
        overlays += polygon(
            [[x * 1200 / 3937, y * 1200 / 3937] for x, y in neighbor["ring"]],
            "#ff8866",
            "Neighbor footprint",
        )
    for index, (x, y, r, h) in enumerate(outdoor["trees"]):
        px, py = pixel(x * 1200 / 3937, y * 1200 / 3937)
        overlays += f'<circle cx="{px}" cy="{py}" r="{r*1200/3937/.08}" fill="none" stroke="#55ff55" stroke-width="1"/><text x="{px}" y="{py}" fill="white" font-size="14">{index}</text>'
    aerial = base64.b64encode((directory / "neighborhood.png").read_bytes()).decode()
    document = f"""<!doctype html><meta charset="utf-8"><title>3014 Cleveland · Geometry evidence</title>
    <style>body{{margin:0;background:#161b20;color:white;font:16px system-ui}}header{{padding:16px;position:sticky;top:0;background:#161b20;z-index:1}}svg{{display:block;width:2000px}}label{{cursor:pointer}}input:not(:checked)~svg #overlay{{display:none}}</style>
    <header>2025 DC aerial · cyan: parcel · yellow: model floor · magenta: GIS building · coral: neighbors · green: estimated tree crowns</header>
    <input id="toggle" type="checkbox" checked><label for="toggle">Show model overlay</label>
    <svg viewBox="650 750 600 650" style="width:min(100%,1100px)" xmlns="http://www.w3.org/2000/svg"><image href="data:image/png;base64,{aerial}" width="2000" height="2000"/><g id="overlay">{overlays}</g></svg>"""
    target = ROOT / "public/geometry-audit.html"
    target.write_text(document, encoding="utf-8")
    print(target)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    figure, axis = plt.subplots(figsize=(10, 10))
    axis.imshow(Image.open(directory / "neighborhood.png"))
    for poly, color in [(outdoor["parcel"], "cyan"), (outdoor["outline"], "magenta")]:
        p = [pixel(x * 1200 / 3937, y * 1200 / 3937) for x, y in poly]
        axis.plot(*zip(*p), color=color, linewidth=1)
    for floor in data["indoor"]["floors"]:
        p = [pixel(*xy) for xy in floor["outline"] + [floor["outline"][0]]]
        axis.plot(*zip(*p), color="yellow", linewidth=1)
    axis.set(xlim=(750, 1250), ylim=(1350, 850))
    axis.set_aspect("equal")
    axis.set_axis_off()
    figure.tight_layout(pad=0)
    figure.savefig(directory / "registered-comparison.png", dpi=140)


if __name__ == "__main__":
    main()
