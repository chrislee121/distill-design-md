# Distill DESIGN.md

> One visual contract per catalog entry. Do not ship the same template with a new title, id, and URL.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Standard-green)](https://agentskills.io)

Distill [Google Labs design.md](https://github.com/google-labs-code/design.md) `alpha` files (YAML + eight fixed sections) from a style catalog and screenshots, then audit the pack for cloned templates.

**简体中文:** [README.md](README.md)

## Install

```
Install this skill: https://github.com/chrislee121/distill-design-md
```

```bash
npx skills add chrislee121/distill-design-md
```

## Usage

```bash
pip install -r requirements.txt
python3 scripts/audit_pack.py --root /path/to/pack
python3 scripts/distill_pack.py --root /path/to/pack
python3 scripts/audit_pack.py --root /path/to/pack
```

Python 3.9+, Pillow, and PyYAML. Pack layout is documented in [SKILL.md](SKILL.md).

This repository does **not** ship large screenshot packs. Point `--root` at your own catalog.

## Smoke test

```bash
python3 scripts/make_mini_pack.py
python3 scripts/distill_pack.py --root examples/mini-pack
python3 scripts/audit_pack.py --root examples/mini-pack
```

Expect `PASS`. Do not commit `examples/mini-pack/`.

## License

MIT. See [LICENSE](LICENSE).
