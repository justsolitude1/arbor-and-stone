"""Rebuild ../index.html from index.src.html by inlining the 3D model and gallery renders.

Usage:  python src/build.py
"""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


html = (ROOT / "src" / "index.src.html").read_text(encoding="utf-8")
html = html.replace("{{GLB}}", b64(ASSETS / "house.glb"))
for name in ["front", "corner", "rear", "living", "aerial"]:
    html = html.replace("{{IMG_%s}}" % name, b64(ASSETS / "renders" / f"{name}.jpg"))
assert "{{" not in html, "unfilled placeholder left in template"

# Wrap in a full document: title, fonts and styles go in <head>, the rest in <body>.
head, body = html.split("</style>", 1)
page = (
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="description" content="Residence No. 01 by Arbor &amp; Stone: a 4,650 sq ft forest home '
    'of cedar, stone and glass, shown as an interactive 3D tour.">\n'
    + head + "</style>\n</head>\n<body>\n" + body.lstrip() + "\n</body>\n</html>\n"
)
(ROOT / "index.html").write_text(page, encoding="utf-8", newline="\n")
print(f"index.html written ({len(page) / 1e6:.1f} MB)")
