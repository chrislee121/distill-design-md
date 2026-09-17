#!/usr/bin/env python3
"""Extract style signals from a public webpage (HTML + a few stylesheets)."""
from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (compatible; distill-design-md/1.0; "
    "+https://github.com/chrislee121/distill-design-md)"
)
MAX_HTML = 1_500_000
MAX_CSS = 400_000
MAX_SHEETS = 6
GENERIC_FONTS = {
    "serif",
    "sans-serif",
    "monospace",
    "cursive",
    "fantasy",
    "system-ui",
    "ui-sans-serif",
    "ui-serif",
    "ui-monospace",
    "emoji",
    "inherit",
    "initial",
    "unset",
    "none",
    "-apple-system",
    "blinkmacsystemfont",
    "ui-rounded",
}

VAR_RE = re.compile(r"--([A-Za-z0-9_-]+)\s*:\s*([^;}{]+)")
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3,8})\b")
RGB_RE = re.compile(
    r"rgba?\(\s*([0-9.]+%?)\s*[, ]\s*([0-9.]+%?)\s*[, ]\s*([0-9.]+%?)",
    re.I,
)
HSL_RE = re.compile(
    r"hsla?\(\s*([0-9.]+)\s*[, ]\s*([0-9.]+)%\s*[, ]\s*([0-9.]+)%",
    re.I,
)
FONT_RE = re.compile(r"font-family\s*:\s*([^;}{]+)", re.I)
RADIUS_RE = re.compile(r"border-radius\s*:\s*([^;}{]+)", re.I)
GOOGLE_FAM_RE = re.compile(r"family=([^&:]+)")

PRIMARY_KEYS = (
    "color-primary",
    "colors-primary",
    "primary",
    "brand-primary",
    "brand",
    "accent",
    "theme-primary",
)
BG_KEYS = (
    "color-background",
    "colors-background",
    "background",
    "bg",
    "page-background",
    "background-color",
)
SURFACE_KEYS = ("color-surface", "colors-surface", "surface", "card", "elevated")
SECONDARY_KEYS = ("color-secondary", "colors-secondary", "secondary")
TERTIARY_KEYS = ("color-tertiary", "colors-tertiary", "tertiary")
SUCCESS_KEYS = ("success", "color-success")
WARNING_KEYS = ("warning", "color-warning")
ERROR_KEYS = ("error", "danger", "destructive", "color-error")

HOST_BRAND = {
    "linear.app": "linear",
    "vercel.com": "vercel-geist",
    "airbnb.com": "airbnb",
    "spotify.com": "spotify",
    "open.spotify.com": "spotify",
    "notion.so": "notion",
    "figma.com": "figma",
    "github.com": "github-primer",
    "stripe.com": "stripe-brand",
    "discord.com": "discord",
    "netflix.com": "netflix-brand",
    "uber.com": "uber-base",
    "adobe.com": "adobe-spectrum",
    "shopify.com": "shopify-polaris",
    "atlassian.com": "atlassian",
    "salesforce.com": "salesforce-lightning",
    "ant.design": "ant-design",
    "developer.apple.com": "apple-hig",
    "m3.material.io": "material-3",
    "material.io": "material-3",
}

BRAND_ALIASES = {
    "vercel": "vercel-geist",
    "stripe": "stripe-brand",
    "github": "github-primer",
    "apple": "apple-hig",
    "material": "material-3",
    "uber": "uber-base",
    "netflix": "netflix-brand",
    "shopify": "shopify-polaris",
    "primer": "github-primer",
}


@dataclass
class PageStyle:
    url: str = ""
    title: str = ""
    description: str = ""
    theme_color: str | None = None
    token_hex: dict[str, str] = field(default_factory=dict)
    fonts: list[str] = field(default_factory=list)
    radii_px: list[float] = field(default_factory=list)
    dark: bool | None = None
    material: str = "flat"
    surface: str = "web-app"
    stylesheet_urls: list[str] = field(default_factory=list)
    hexes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    fetched: bool = False


class _DocParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_bits: list[str] = []
        self.in_title = False
        self.in_style = False
        self.style_bits: list[str] = []
        self.metas: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.inline: list[str] = []
        self.html_class = ""
        self.body_class = ""
        self.color_scheme = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self.in_title = True
        elif tag == "style":
            self.in_style = True
        elif tag == "meta":
            key = (d.get("name") or d.get("property") or d.get("http-equiv") or "").lower()
            if key and d.get("content"):
                self.metas[key] = d["content"]
        elif tag == "link":
            self.links.append(d)
        elif tag == "html":
            self.html_class = d.get("class") or ""
            self.color_scheme = d.get("data-color-mode") or d.get("data-theme") or ""
        elif tag == "body":
            self.body_class = d.get("class") or ""
        if d.get("style"):
            self.inline.append(d["style"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_bits.append(data)
        if self.in_style:
            self.style_bits.append(data)


def fetch_text(url: str, max_bytes: int) -> tuple[str, str]:
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,text/css,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(req, timeout=20) as resp:
        raw = resp.read(max_bytes + 1)[:max_bytes]
        charset = resp.headers.get_content_charset() or "utf-8"
        final = resp.geturl()
    return raw.decode(charset, errors="replace"), final


def _channel(raw: str) -> float:
    raw = raw.strip()
    if raw.endswith("%"):
        return max(0.0, min(255.0, float(raw[:-1]) * 2.55))
    return max(0.0, min(255.0, float(raw)))


def parse_css_color(value: str) -> tuple[int, int, int] | None:
    if not value:
        return None
    value = value.strip().split()[0] if value.strip().startswith("#") else value.strip()
    m = HEX_RE.search(value)
    if m:
        h = m.group(0)[1:]
        if len(h) in (4, 8):
            h = h[:3] if len(h) == 4 else h[:6]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if re.fullmatch(r"[0-9A-Fa-f]{6}", h):
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    m = RGB_RE.search(value)
    if m:
        return tuple(int(round(_channel(x))) for x in m.groups())  # type: ignore[return-value]
    m = HSL_RE.search(value)
    if m:
        h, s, l = float(m.group(1)), float(m.group(2)) / 100, float(m.group(3)) / 100
        r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
        return int(r * 255), int(g * 255), int(b * 255)
    return None


def _sat(rgb: tuple[int, int, int]) -> float:
    mx, mn = max(rgb), min(rgb)
    if mx == 0:
        return 0.0
    return (mx - mn) / mx


def css_vars(text: str) -> dict[str, str]:
    return {m.group(1).lower(): m.group(2).strip() for m in VAR_RE.finditer(text)}


def resolve_var(value: str, variables: dict[str, str], depth: int = 0) -> str | None:
    value = value.strip().rstrip(";")
    m = re.match(r"var\(\s*--([^),]+)(?:,\s*(.+))?\)", value, re.I)
    if m and depth < 5:
        key = m.group(1).lower()
        if key in variables:
            return resolve_var(variables[key], variables, depth + 1)
        if m.group(2):
            return resolve_var(m.group(2), variables, depth + 1)
        return None
    return value


def _pick_key(variables: dict[str, str], names: Iterable[str]) -> str | None:
    keys = list(variables)
    for name in names:
        for k in keys:
            if k == name or k.endswith("-" + name):
                return k
    return None


def font_names(blob: str) -> list[str]:
    found: list[str] = []
    for m in FONT_RE.finditer(blob):
        for part in m.group(1).split(","):
            name = part.strip().strip("'\"").strip()
            if name and name.lower() not in GENERIC_FONTS and name not in found:
                found.append(name)
    for m in GOOGLE_FAM_RE.finditer(blob):
        name = m.group(1).replace("+", " ")
        if name and name not in found:
            found.append(name)
    return found[:8]


def radii(blob: str) -> list[float]:
    out: list[float] = []
    for m in RADIUS_RE.finditer(blob):
        first = m.group(1).split()[0]
        n = re.match(r"([0-9.]+)px", first)
        if n:
            val = float(n.group(1))
            if 2 <= val <= 48:
                out.append(val)
    return out


def brand_key_for(host: str, slug: str = "", name: str = "") -> str | None:
    host = (host or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host in HOST_BRAND:
        return HOST_BRAND[host]
    for suffix, key in HOST_BRAND.items():
        if host == suffix or host.endswith("." + suffix):
            return key
    slug = (slug or "").lower()
    name_slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    for token in (slug, name_slug):
        if token in HOST_BRAND.values() or token in BRAND_ALIASES.values():
            return token
        if token in BRAND_ALIASES:
            return BRAND_ALIASES[token]
    return None


def _collect_hexes(blob: str) -> list[str]:
    out = []
    for m in HEX_RE.finditer(blob):
        rgb = parse_css_color(m.group(0))
        if rgb:
            out.append("#{:02X}{:02X}{:02X}".format(*rgb))
    return out


def _apply_tokens(page: PageStyle, blob: str) -> None:
    variables = css_vars(blob)
    mapping = {
        "primary": PRIMARY_KEYS,
        "background": BG_KEYS,
        "surface": SURFACE_KEYS,
        "secondary": SECONDARY_KEYS,
        "tertiary": TERTIARY_KEYS,
        "success": SUCCESS_KEYS,
        "warning": WARNING_KEYS,
        "error": ERROR_KEYS,
    }
    for semantic, names in mapping.items():
        key = _pick_key(variables, names)
        if not key:
            continue
        resolved = resolve_var(variables[key], variables)
        rgb = parse_css_color(resolved or "")
        if rgb and (semantic in {"background", "surface"} or _sat(rgb) >= 0.12 or semantic != "primary"):
            page.token_hex[semantic] = "#{:02X}{:02X}{:02X}".format(*rgb)
    page.fonts = list(dict.fromkeys(page.fonts + font_names(blob)))
    page.radii_px.extend(radii(blob))
    page.hexes.extend(_collect_hexes(blob))
    low = blob.lower()
    if "backdrop-filter" in low or "saturate(" in low:
        page.material = "glass"
    if re.search(r"color-scheme\s*:\s*dark", low):
        page.dark = True
    elif re.search(r"color-scheme\s*:\s*light", low) and page.dark is not True:
        page.dark = False


def parse_document(html: str, base_url: str = "", fetch_css: bool = False) -> PageStyle:
    parser = _DocParser()
    try:
        parser.feed(html)
    except Exception as exc:
        page = PageStyle(url=base_url, errors=[f"HTML 解析失败: {exc}"])
        return page
    page = PageStyle(url=base_url)
    page.title = re.sub(r"\s+", " ", "".join(parser.title_bits)).strip()
    page.description = (
        parser.metas.get("description")
        or parser.metas.get("og:description")
        or ""
    ).strip()
    theme = parser.metas.get("theme-color")
    if theme:
        rgb = parse_css_color(theme)
        if rgb:
            page.theme_color = "#{:02X}{:02X}{:02X}".format(*rgb)
            if _sat(rgb) >= 0.25:
                page.token_hex.setdefault("primary", page.theme_color)
    classes = f"{parser.html_class} {parser.body_class} {parser.color_scheme}".lower()
    if "dark" in classes:
        page.dark = True
    if parser.metas.get("apple-mobile-web-app-capable") == "yes":
        page.surface = "mobile-app"
    blob = "\n".join(parser.style_bits + parser.inline)
    _apply_tokens(page, blob)
    hrefs: list[str] = []
    for link in parser.links:
        rel = (link.get("rel") or "").lower()
        href = link.get("href") or ""
        if not href:
            continue
        if "stylesheet" in rel or link.get("as") == "style":
            hrefs.append(urljoin(base_url, href))
        if "fonts.googleapis.com" in href:
            page.fonts = list(dict.fromkeys(page.fonts + font_names(href)))
    page.stylesheet_urls = hrefs[:MAX_SHEETS]
    if fetch_css and base_url:
        host = urlparse(base_url).hostname or ""
        for css_url in page.stylesheet_urls:
            css_host = urlparse(css_url).hostname or ""
            scheme = urlparse(css_url).scheme
            if scheme not in {"http", "https"}:
                continue
            if css_host != host and "fonts.googleapis.com" not in css_host:
                continue
            try:
                text, _final = fetch_text(css_url, MAX_CSS)
            except Exception as exc:
                page.errors.append(f"样式表失败 {css_url}: {exc}")
                continue
            _apply_tokens(page, text)
            page.fetched = True
    if page.theme_color and "primary" not in page.token_hex:
        rgb = parse_css_color(page.theme_color)
        if rgb and _sat(rgb) >= 0.22:
            page.token_hex["primary"] = page.theme_color
    return page


def fetch_page(url: str) -> PageStyle:
    try:
        html, final = fetch_text(url, MAX_HTML)
    except HTTPError as exc:
        return PageStyle(url=url, errors=[f"HTTP {exc.code} {url}"])
    except URLError as exc:
        return PageStyle(url=url, errors=[f"无法打开 {url}: {exc.reason}"])
    except Exception as exc:
        return PageStyle(url=url, errors=[f"无法打开 {url}: {exc}"])
    page = parse_document(html, final, fetch_css=True)
    page.url = final
    page.fetched = True
    return page
