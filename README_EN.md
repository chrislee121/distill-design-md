# Distill DESIGN.md

> One visual contract per style. Do not ship the same template with a new title, id, and URL.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Standard-green)](https://agentskills.io)

Identify a visual style from a **page URL, screenshots, and notes**, or from a catalog pack, then distill [Google Labs design.md](https://github.com/google-labs-code/design.md) `alpha` files (YAML + eight fixed sections). Packs can also be audited for cloned templates.

**简体中文:** [README.md](README.md)

## Install

```
Install this skill: https://github.com/chrislee121/distill-design-md
```

```bash
npx skills add chrislee121/distill-design-md
```

## Usage

One site or screenshot:

```bash
python3 scripts/distill_entry.py \
  --url https://example.com \
  --screenshot ./shot.png \
  --name "Example" \
  --out ./Example.DESIGN.md
```

A catalog pack:

```bash
pip install -r requirements.txt
python3 scripts/audit_pack.py --root /path/to/pack
python3 scripts/distill_pack.py --root /path/to/pack
python3 scripts/audit_pack.py --root /path/to/pack
```

Python 3.9+, Pillow, and PyYAML. See [SKILL.md](SKILL.md). `--url` fetches that page (and a few same-host stylesheets) locally; it is not a site crawler.

This repository does **not** ship large screenshot packs.

## Smoke test

```bash
python3 scripts/make_mini_pack.py
python3 scripts/distill_pack.py --root examples/mini-pack
python3 scripts/audit_pack.py --root examples/mini-pack
python3 scripts/test_distill_entry.py
```

Expect `PASS`. Do not commit `examples/mini-pack/`.

## License

MIT. See [LICENSE](LICENSE).
