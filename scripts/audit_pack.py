#!/usr/bin/env python3
"""Audit a style pack's DESIGN.md files for clone-template quality issues.

Exit 0 if gates pass, 1 otherwise. Prints JSON summary to stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SECTIONS = [
    "Overview",
    "Colors",
    "Typography",
    "Layout",
    "Elevation & Depth",
    "Shapes",
    "Components",
    "Do's and Don'ts",
]


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def find_pack_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / "catalog" / "entries.jsonl").exists() and (p / "design-md").is_dir():
            return p
    raise SystemExit("找不到风格包根目录（需要 catalog/entries.jsonl 与 design-md/）")


def resolve_asset(root: Path, rec: dict) -> Path | None:
    rel = rec.get("screenshotPath") or ""
    if rel:
        p = root / rel
        if p.exists():
            return p
    eid = rec.get("id") or ""
    for folder in (root / "brand-style-assets" / "by-id", root / "screenshots" / "by-id"):
        hits = list(folder.glob(f"{eid}.*")) if folder.is_dir() else []
        if hits:
            return hits[0]
    return None


def audit(root: Path) -> dict:
    jsonl = root / "catalog" / "entries.jsonl"
    md_dir = root / "design-md"
    rows = [json.loads(l) for l in jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
    files = sorted(md_dir.glob("sty-*.DESIGN.md")) + sorted(md_dir.glob("*.DESIGN.md"))
    files = [p for p in files if not p.name.startswith("_")]
    files = list(dict.fromkeys(files))

    pal = Counter()
    how = Counter()
    bodies = Counter()
    missing_sec = 0
    yaml_mismatch = 0
    broken_ref = 0
    luxury = 0
    by_site = defaultdict(Counter)
    id_site = {r["id"]: r.get("sourceSite") or "?" for r in rows}

    for p in files:
        t = p.read_text(encoding="utf-8")
        bodies[hashlib.md5(t.encode()).hexdigest()] += 1
        if "Luxury gold" in t:
            luxury += 1
        m = re.search(r'primary:\s*"([^"]+)"', t)
        primary = m.group(1) if m else "?"
        pal[primary] += 1
        eid = p.name.split("__", 1)[0].replace(".DESIGN.md", "")
        by_site[id_site.get(eid, "?")][primary] += 1
        hm = re.search(r"^How to use: (.+)$", t, re.M)
        if hm:
            how[hm.group(1)] += 1
        for sec in SECTIONS:
            if f"## {sec}" not in t:
                missing_sec += 1
        body_p = re.search(r"- \*\*primary\*\* \(`([^`]+)`\)", t)
        if body_p and m and body_p.group(1).upper() != m.group(1).upper():
            yaml_mismatch += 1
        fm = t.split("---", 2)
        fm_body = fm[1] if len(fm) > 2 else ""
        for ref in re.findall(r"\{colors\.([A-Za-z0-9_]+)\}", t):
            if f"{ref}:" not in fm_body:
                broken_ref += 1

    shot_hash = Counter()
    missing_shots = []
    for rec in rows:
        shot = resolve_asset(root, rec)
        if not shot:
            missing_shots.append(rec.get("id"))
            continue
        shot_hash[file_md5(shot)] += 1

    clone_groups = [(h, n) for h, n in shot_hash.items() if n >= 8]
    clone_fail = []
    for rec in rows:
        shot = resolve_asset(root, rec)
        if not shot:
            continue
        h = file_md5(shot)
        if shot_hash[h] < 8:
            continue
        p = root / (rec.get("templatePath") or f"design-md/{rec['id']}.DESIGN.md")
        if not p.exists():
            matches = list(md_dir.glob(f"{rec['id']}*.DESIGN.md"))
            p = matches[0] if matches else p
        if not p.exists():
            continue
        m = re.search(r'primary:\s*"([^"]+)"', p.read_text(encoding="utf-8"))
        if m:
            clone_fail.append((h, rec["id"], m.group(1)))

    clone_palette = defaultdict(set)
    for h, _eid, prim in clone_fail:
        clone_palette[h].add(prim)
    cloned_same_primary = [
        {"hash": h[:8], "n": shot_hash[h], "unique_primary": len(prims)}
        for h, prims in clone_palette.items()
        if len(prims) <= 1 and shot_hash[h] >= 8
    ]

    unique_files = sum(1 for n in bodies.values() if n == 1)
    max_how = how.most_common(1)[0][1] if how else 0
    gates = {
        "unique_files": unique_files == len(files) and len(files) == len(rows),
        "how_to_unique": max_how <= 1,
        "yaml_match": yaml_mismatch == 0,
        "token_refs": broken_ref == 0,
        "sections": missing_sec == 0,
        "no_luxury_gold": luxury == 0,
        "shots_present": len(missing_shots) == 0,
        "cloned_shots_have_unique_primary": len(cloned_same_primary) == 0,
    }
    return {
        "root": str(root),
        "entries": len(rows),
        "files": len(files),
        "unique_files": unique_files,
        "unique_primaries": len(pal),
        "top_primaries": pal.most_common(8),
        "unique_how": len(how),
        "max_how_clone": max_how,
        "yaml_mismatch": yaml_mismatch,
        "broken_ref": broken_ref,
        "missing_sections": missing_sec,
        "luxury_gold": luxury,
        "missing_shots": missing_shots[:20],
        "screenshot_clone_groups": [{"n": n, "hash": h[:8]} for h, n in sorted(clone_groups, key=lambda x: -x[1])[:10]],
        "cloned_same_primary": cloned_same_primary,
        "by_site": {
            k: {"n": sum(v.values()), "unique_primary": len(v), "top": v.most_common(1)[0]}
            for k, v in sorted(by_site.items(), key=lambda kv: -sum(kv[1].values()))
        },
        "gates": gates,
        "ok": all(gates.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="只输出 JSON")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else find_pack_root(Path.cwd())
    stats = audit(root)
    if args.json:
        json.dump(stats, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"pack {stats['root']}")
        print(f"files {stats['unique_files']}/{stats['files']} unique  primaries {stats['unique_primaries']}")
        print(f"how-to unique {stats['unique_how']} max_clone {stats['max_how_clone']}")
        print(f"yaml_mismatch {stats['yaml_mismatch']} broken_ref {stats['broken_ref']} missing_sec {stats['missing_sections']}")
        print("by site", stats["by_site"])
        print("clone screenshot groups", stats["screenshot_clone_groups"])
        failed = [k for k, v in stats["gates"].items() if not v]
        print("FAIL" if failed else "PASS", failed or "all gates")
    raise SystemExit(0 if stats["ok"] else 1)


if __name__ == "__main__":
    main()
