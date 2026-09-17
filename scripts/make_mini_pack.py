#!/usr/bin/env python3
"""Write a tiny fixture pack so CI can distill + audit without shipping screenshots."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / "examples" / "mini-pack"

SAMPLES = (
    ("sty-0001", "coral-dashboard", "#E24A3A", "#F7F1EA", "https://example.com/coral"),
    ("sty-0002", "indigo-console", "#3D5AFE", "#0B1020", "https://example.com/indigo"),
)


def main() -> None:
    assets = ROOT / "brand-style-assets" / "by-id"
    md = ROOT / "design-md"
    cat = ROOT / "catalog"
    assets.mkdir(parents=True, exist_ok=True)
    md.mkdir(parents=True, exist_ok=True)
    cat.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for eid, slug, fill, bg, url in SAMPLES:
        img = Image.new("RGB", (800, 500), bg)
        draw = ImageDraw.Draw(img)
        draw.rectangle((80, 80, 720, 200), fill=fill)
        draw.rectangle((80, 240, 360, 420), fill="#FFFFFF")
        img.save(assets / f"{eid}.png")
        rows.append(
            {
                "id": eid,
                "slug": slug,
                "title": slug.replace("-", " ").title(),
                "titleZh": slug,
                "sourceSite": "example",
                "sourceUrl": url,
                "originalSiteUrl": url,
                "surface": "web-app",
                "screenshotPath": f"brand-style-assets/by-id/{eid}.png",
                "styleTags": ["product"],
            }
        )
    (cat / "entries.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(ROOT)


if __name__ == "__main__":
    main()
