# 蒸馏 DESIGN.md

> 一份条目一份独立视觉合同。禁止同一套稿只换标题、编号、链接。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Standard-green)](https://agentskills.io)
[![skills.sh](https://img.shields.io/badge/skills.sh-Compatible-blue)](https://skills.sh)

从 **网页链接、截图、备注** 或风格目录，识别公开可见的色板/字体/形状，蒸馏出符合 [Google Labs design.md](https://github.com/google-labs-code/design.md) `alpha` 的 `DESIGN.md`（YAML + 固定八节）。风格包还可以审核是否套模板。

基于 [Agent Skills](https://agentskills.io)，可用于 Cursor、Claude Code、Codex 等兼容 runtime。

**Other languages:** [English](README_EN.md)

---

## 它做什么

1. **单条识别：** 网页 URL（HTML/CSS）、截图、名称/备注 → 识别主色、画布、字体、深浅 → 写一份 DESIGN.md
2. **风格包：** 读 `catalog/entries.jsonl` 和每条截图，一份条目一份合同
3. 取色优先级：公开品牌/主题表 → 网页 CSS 变量 → 截图量化 → 名称/URL 色相；包内还有上游 YAML 与克隆截图分流
4. 写出 YAML + 八节：Overview → Colors → Typography → Layout → Elevation & Depth → Shapes → Components → Do's and Don'ts
5. 风格包用硬门槛审核：整文件不重复、How to use 不共用、YAML 与正文主色一致、克隆截图组不能共用一个 primary

本仓库 **不包含** 大型风格包或截图素材。

`--url` 只请求用户给出的页面和同主机少量 CSS，结果留在本地。不是全站爬虫。

## 安装

对 Agent 说：

```
帮我安装这个 skill：https://github.com/chrislee121/distill-design-md
```

或：

```bash
npx skills add chrislee121/distill-design-md
```

手动路径见 [references/runtimes.md](references/runtimes.md)。

## 用法

单条（链接 + 截图）：

```
根据 https://example.com 和这张截图识别风格，蒸馏一份 DESIGN.md
```

```bash
python3 scripts/distill_entry.py \
  --url https://example.com \
  --screenshot ./shot.png \
  --name "Example" \
  --out ./Example.DESIGN.md
```

风格包：

```
按 distill-design-md 审核这个风格包，再全量蒸馏 DESIGN.md
```

```bash
pip install -r requirements.txt
python3 scripts/audit_pack.py --root /path/to/pack
python3 scripts/distill_pack.py --root /path/to/pack
python3 scripts/audit_pack.py --root /path/to/pack
```

需要 Python 3.9+、Pillow、PyYAML。

约定见 [SKILL.md](SKILL.md)。规范与门槛见 [references/spec.md](references/spec.md)、[references/quality-gates.md](references/quality-gates.md)。

## 最小自检

```bash
python3 scripts/make_mini_pack.py
python3 scripts/distill_pack.py --root examples/mini-pack
python3 scripts/audit_pack.py --root examples/mini-pack
python3 scripts/test_distill_entry.py
```

风格包应输出 `PASS`。`examples/mini-pack/` 是生成物，不要提交。

## 对外口径

蒸馏结果是 Agent 草稿：按公开可见的截图、网页 CSS 或 YAML 重建 token 与气质。不是官方品牌包，也不能当成可商用的完整设计系统。

## 许可

MIT。见 [LICENSE](LICENSE)。
