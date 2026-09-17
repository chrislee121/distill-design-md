#!/usr/bin/env python3
"""Offline tests for single-entry identify + distill."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURE = ROOT / "tests" / "fixtures" / "coral.html"


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd or ROOT),
        check=True,
        capture_output=True,
        text=True,
    )


def write_shot(path: Path, fill: str, bg: str) -> None:
    img = Image.new("RGB", (800, 500), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle((80, 80, 720, 200), fill=fill)
    draw.rectangle((80, 240, 360, 420), fill="#FFFFFF")
    img.save(path)


def assert_md(text: str, primary: str) -> None:
    for sec in (
        "## Overview",
        "## Colors",
        "## Typography",
        "## Layout",
        "## Elevation & Depth",
        "## Shapes",
        "## Components",
        "## Do's and Don'ts",
    ):
        assert sec in text, sec
    assert f'primary: "{primary}"' in text
    assert "How to use:" in text
    assert "{colors.primary}" in text


def main() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import page_style as web

    page = web.parse_document(FIXTURE.read_text(encoding="utf-8"), "https://example.com/coral")
    assert page.token_hex.get("primary") == "#E24A3A", page.token_hex
    assert page.token_hex.get("background") == "#F7F1EA"
    assert any(f.lower() == "inter" for f in page.fonts), page.fonts
    assert web.brand_key_for("linear.app") == "linear"
    assert web.brand_key_for("www.vercel.com", name="Vercel") == "vercel-geist"

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        shot = tmp / "coral.png"
        write_shot(shot, "#E24A3A", "#F7F1EA")
        html_out = tmp / "from-html.DESIGN.md"
        html_id = run(
            [
                str(SCRIPTS / "distill_entry.py"),
                "--html",
                str(FIXTURE),
                "--url",
                "https://example.com/coral",
                "--name",
                "Coral Dashboard",
                "--out",
                str(html_out),
                "--json",
            ]
        )
        report = json.loads(html_id.stdout)
        assert report["colors"]["primary"] == "#E24A3A", report["colors"]
        assert_md(html_out.read_text(encoding="utf-8"), "#E24A3A")

        shot_out = tmp / "from-shot.DESIGN.md"
        run(
            [
                str(SCRIPTS / "distill_entry.py"),
                "--screenshot",
                str(shot),
                "--name",
                "Coral Shot",
                "--notes",
                "product, warm",
                "--url",
                "https://example.com/coral-shot",
                "--offline",
                "--out",
                str(shot_out),
            ]
        )
        text = shot_out.read_text(encoding="utf-8")
        assert_md(text, "#E24A3A")
        assert "https://example.com/coral-shot" in text

        both_out = tmp / "from-both.DESIGN.md"
        both = run(
            [
                str(SCRIPTS / "distill_entry.py"),
                "--html",
                str(FIXTURE),
                "--screenshot",
                str(shot),
                "--url",
                "https://example.com/coral",
                "--name",
                "Coral Both",
                "--identify-only",
            ]
        )
        ident = json.loads(both.stdout)
        assert ident["colors"]["primary"] == "#E24A3A"
        assert "screenshot" in ident["sources"]
        run(
            [
                str(SCRIPTS / "distill_entry.py"),
                "--html",
                str(FIXTURE),
                "--screenshot",
                str(shot),
                "--url",
                "https://example.com/coral",
                "--name",
                "Coral Both",
                "--out",
                str(both_out),
            ]
        )
        assert_md(both_out.read_text(encoding="utf-8"), "#E24A3A")

        only_name = run(
            [
                str(SCRIPTS / "distill_entry.py"),
                "--name",
                "Midnight Harbor",
                "--notes",
                "dark, editorial serif",
                "--identify-only",
            ]
        )
        named = json.loads(only_name.stdout)
        assert named["title"] == "Midnight Harbor"
        assert named["colors"]["primary"].startswith("#")

    print("test_distill_entry ok")


if __name__ == "__main__":
    main()
