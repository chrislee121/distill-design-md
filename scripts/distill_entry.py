#!/usr/bin/env python3
"""Identify a visual style from URL / HTML / screenshots / notes, then distill one DESIGN.md."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import distill_pack as dp
import page_style as web

GENERIC_TITLE_SUFFIX = re.compile(r"\s*[|\-—·].*$")


def slugify(text: str) -> str:
    text = re.sub(r"^https?://", "", text or "", flags=re.I)
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (text[:60] or "style").rstrip("-")


def host_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def split_tags(notes: str) -> list[str]:
    if not notes:
        return []
    parts = re.split(r"[,，、|/]+", notes)
    return [p.strip() for p in parts if p.strip()]


def guess_title(name: str, page: web.PageStyle | None, url: str, shots: list[Path]) -> str:
    if name.strip():
        return name.strip()
    if page and page.title:
        return GENERIC_TITLE_SUFFIX.sub("", page.title).strip() or page.title.strip()
    if url:
        host = host_of(url)
        return host.split(".")[0].title() if host else url
    if shots:
        return shots[0].stem.replace("_", " ").replace("-", " ")
    return "Untitled style"


def make_rec(
    *,
    title: str,
    slug: str,
    url: str,
    notes: str,
    surface: str,
    page: web.PageStyle | None,
    brand: str | None,
    fonts: tuple[str, str, str] | None,
) -> dict:
    tags = split_tags(notes)
    if page and page.material == "glass" and "glass" not in " ".join(tags).lower():
        tags.append("glass")
    host = host_of(url)
    rec = {
        "id": "sty-" + hashlib.md5((url or slug).encode()).hexdigest()[:8],
        "slug": brand or slug,
        "title": title,
        "titleZh": title,
        "sourceSite": host.split(".")[0] if host else "web",
        "sourceUrl": url,
        "originalSiteUrl": url,
        "surface": surface,
        "styleTags": tags,
        "atmosphereHint": notes.strip(),
        "layoutNotes": (page.description if page else "") or notes.strip(),
        "materialHint": (page.material if page else "") or "flat",
        "sourceType": "design-system" if brand and brand.endswith("hig") else "site",
    }
    if fonts:
        rec["fontFamilies"] = list(fonts)
    return rec


def extract_shots(paths: list[Path]) -> tuple[dict | None, Path | None, list[str]]:
    notes: list[str] = []
    best = None
    best_path = None
    best_score = -1.0
    for path in paths:
        if not path.exists():
            notes.append(f"截图不存在: {path}")
            continue
        extracted = dp.extract_from_image(path)
        if not extracted:
            notes.append(f"截图无法解码: {path}")
            continue
        weak = bool(extracted.get("_weak"))
        primary = extracted["primary"]
        score = (0.2 if weak else 1.0) * dp.sat(primary)
        if score > best_score:
            best, best_path, best_score = extracted, path, score
    return best, best_path, notes


def page_rgb(page: web.PageStyle | None) -> dict[str, tuple[int, int, int]]:
    if not page:
        return {}
    out = {}
    for key, hx in page.token_hex.items():
        out[key] = dp.hex_rgb(hx)
    return out


def pick_fonts(page: web.PageStyle | None, rec: dict) -> tuple[str, str, str]:
    display, body, mono = dp.pick_type(rec)
    if not page or not page.fonts:
        return display, body, mono
    named = page.fonts
    body_c = named[0]
    display_c = named[0]
    mono_c = mono
    for fam in named:
        low = fam.lower()
        if "mono" in low or "code" in low:
            mono_c = fam
        elif "display" in low or "headline" in low:
            display_c = fam
        else:
            body_c = fam
    if display_c == body_c and len(named) > 1 and "mono" not in named[1].lower():
        display_c = named[0]
        body_c = named[1] if named[1] != named[0] else body_c
    return display_c, body_c, mono_c


def rounded_from(page: web.PageStyle | None) -> dict[str, str] | None:
    if not page or not page.radii_px:
        return None
    vals = sorted(page.radii_px)
    mid = vals[len(vals) // 2]
    return {
        "sm": f"{max(2, round(mid * 0.5))}px",
        "md": f"{round(mid)}px",
        "lg": f"{round(mid * 1.6)}px",
        "full": "9999px",
    }


def merge_palette(
    rec: dict,
    page: web.PageStyle | None,
    shot: dict | None,
    brand: str | None,
) -> tuple[dict[str, tuple[int, int, int]], str]:
    origins: list[str] = []
    named = None
    brand_label = brand
    if brand and brand in dp.BRAND_COLORS:
        named = dp.BRAND_COLORS[brand]
    elif brand and brand.startswith("theme-"):
        key = brand[6:]
        if key in dp.THEME_COLORS:
            named = dp.THEME_COLORS[key]
            brand_label = key
    if named:
        if shot:
            canvas = {k: v for k, v in shot.items() if not str(k).startswith("_")}
            colors = dp.apply_named(canvas, named)
            origins.append(f"公开品牌 `{brand_label}` 叠在截图表面上")
        else:
            colors = dp.from_named(named)
            origins.append(f"公开品牌 `{brand_label}`")
        return colors, "；".join(origins)

    tokens = page_rgb(page)
    if shot and not shot.get("_weak"):
        colors = {k: v for k, v in shot.items() if not str(k).startswith("_")}
        origins.append("截图量化")
        if tokens.get("primary") and dp.sat(tokens["primary"]) >= 0.22:
            colors["primary"] = tokens["primary"]
            origins.append("网页 CSS 主色")
        for key in ("secondary", "tertiary"):
            if key in tokens:
                colors[key] = tokens[key]
        return dp.complete_colors(colors), "；".join(origins)

    if tokens.get("primary"):
        parts = dict(tokens)
        if shot:
            parts.setdefault("background", shot["background"])
            parts.setdefault("surface", shot["surface"])
            origins.append("网页 CSS token，画布取自截图")
        else:
            origins.append("网页 CSS 变量 / theme-color")
        return dp.complete_colors(parts), "；".join(origins)

    if shot:
        weak = bool(shot.pop("_weak", False)) if "_weak" in shot else False
        canvas = {k: v for k, v in shot.items() if not str(k).startswith("_")}
        if not weak:
            return dp.complete_colors(canvas), "截图量化"
        dark = dp.rel_lum(canvas["background"]) < 0.35
        named_pal = dp.name_palette(rec, dark=dark)
        named_pal["background"] = canvas["background"]
        named_pal["surface"] = canvas["surface"]
        return dp.complete_colors(named_pal), "截图偏中性，主色按名称/链接色相蒸馏"

    if page:
        scored: list[tuple[float, tuple[int, int, int]]] = []
        bg = tokens.get("background")
        for hx in page.hexes:
            rgb = dp.hex_rgb(hx)
            if dp.sat(rgb) < 0.22:
                continue
            if bg and math.dist(rgb, bg) < 18:
                continue
            scored.append((dp.sat(rgb), rgb))
        if scored:
            primary = sorted(scored, key=lambda kv: kv[0], reverse=True)[0][1]
            parts = {"primary": primary}
            if bg:
                parts["background"] = bg
            return dp.complete_colors(parts), "网页出现的强调色"

    return dp.name_palette(rec), "按名称/链接色相蒸馏（无可靠取色源）"


def identify_and_distill(
    *,
    url: str,
    html_path: Path | None,
    screenshots: list[Path],
    name: str,
    notes: str,
    surface: str,
    fetch: bool,
) -> tuple[str, dict, dict]:
    page = None
    sources: list[str] = []
    warnings: list[str] = []
    if html_path:
        page = web.parse_document(html_path.read_text(encoding="utf-8"), url or str(html_path), fetch_css=False)
        sources.append("html")
        warnings.extend(page.errors)
    elif url and fetch:
        page = web.fetch_page(url)
        sources.append("url")
        warnings.extend(page.errors)
        if page.url:
            url = page.url
    elif url:
        sources.append("url")

    if screenshots:
        sources.append("screenshot")
    if notes:
        sources.append("notes")

    shot, shot_path, shot_notes = extract_shots(screenshots)
    warnings.extend(shot_notes)
    title = guess_title(name, page, url, screenshots)
    slug = slugify(name or (page.title if page else "") or host_of(url) or title)
    brand = web.brand_key_for(host_of(url), slug, title)
    if surface == "auto":
        surface = page.surface if page else "web-app"
        if notes and re.search(r"ios|android|mobile|app", notes, re.I):
            surface = "mobile-app"
    rec = make_rec(
        title=title,
        slug=slug,
        url=url,
        notes=notes,
        surface=surface,
        page=page,
        brand=brand,
        fonts=None,
    )
    colors, origin = merge_palette(rec, page, shot, brand)
    fonts = pick_fonts(page, rec)
    rec["fontFamilies"] = list(fonts)
    extra = {
        "description": (page.description if page else "") or notes,
        "rounded": rounded_from(page),
        "typography": {
            "h1": {"fontFamily": fonts[0]},
            "body": {"fontFamily": fonts[1]},
            "mono": {"fontFamily": fonts[2]},
        },
    }
    shot_name = shot_path.name if shot_path else (host_of(url) or "page")
    md = dp.build_md(rec, colors, shot_name, origin, extra)
    report = {
        "title": title,
        "slug": rec["slug"],
        "id": rec["id"],
        "url": url,
        "brand": brand,
        "origin": origin,
        "sources": sources,
        "surface": rec["surface"],
        "dark": dp.rel_lum(colors["background"]) < 0.35,
        "fonts": {"display": fonts[0], "body": fonts[1], "mono": fonts[2]},
        "colors": {k: dp.rgb_hex(v) for k, v in colors.items() if not str(k).startswith("_")},
        "warnings": warnings,
        "page_title": page.title if page else "",
        "theme_color": page.theme_color if page else None,
        "css_tokens": page.token_hex if page else {},
    }
    return md, report, rec


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从网页链接、本地 HTML、截图和备注识别风格并蒸馏一份 DESIGN.md。"
    )
    parser.add_argument("--url", default="", help="公开网页 URL（会发 HTTP 请求）")
    parser.add_argument("--html", type=Path, default=None, help="本地 HTML（不联网，适合离线/CI）")
    parser.add_argument("--screenshot", action="append", default=[], type=Path, help="截图路径，可重复")
    parser.add_argument("--name", default="", help="风格名称")
    parser.add_argument("--notes", default="", help="补充：气质、行业、深浅、材质等")
    parser.add_argument("--surface", default="auto", choices=["auto", "web-app", "mobile-app"])
    parser.add_argument("--out", type=Path, default=None, help="写出路径，默认 ./<slug>.DESIGN.md")
    parser.add_argument("--identify-only", action="store_true", help="只输出识别 JSON，不写 md")
    parser.add_argument("--offline", action="store_true", help="不抓取 URL，只使用已给的 HTML/截图/名称")
    parser.add_argument("--json", action="store_true", help="识别结果打到 stdout（写文件时默认打 stderr）")
    args = parser.parse_args()
    shots = list(args.screenshot)
    if not args.url and not args.html and not shots and not args.name:
        raise SystemExit("至少提供 --url、--html、--screenshot 或 --name")

    md, report, rec = identify_and_distill(
        url=args.url,
        html_path=args.html,
        screenshots=shots,
        name=args.name,
        notes=args.notes,
        surface=args.surface,
        fetch=bool(args.url) and not args.offline and args.html is None,
    )
    if args.identify_only:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return

    out = args.out
    if out is None:
        out = Path(f"{rec['slug']}.DESIGN.md")
    if str(out) == "-":
        sys.stdout.write(md)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    report["out"] = str(out.resolve())
    sink = sys.stdout if args.json else sys.stderr
    json.dump(report, sink, ensure_ascii=False, indent=2)
    sink.write("\n")
    if not args.json:
        print(out.resolve())


if __name__ == "__main__":
    main()
