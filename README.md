# 蒸馏 DESIGN.md

> 一份条目一份独立视觉合同。禁止同一套稿只换标题、编号、链接。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Standard-green)](https://agentskills.io)
[![skills.sh](https://img.shields.io/badge/skills.sh-Compatible-blue)](https://skills.sh)

从风格目录 + 截图蒸馏出符合 [Google Labs design.md](https://github.com/google-labs-code/design.md) `alpha` 的 `DESIGN.md`（YAML + 固定八节），并审核是否套模板。

基于 [Agent Skills](https://agentskills.io)，可用于 Cursor、Claude Code、Codex 等兼容 runtime。

**Other languages:** [English](README_EN.md)

---

## 它做什么

1. 读 `catalog/entries.jsonl` 和每条截图
2. 按优先级取色：上游 DESIGN.md YAML → 公开品牌/设计系统/主题表 → 独立截图量化 → 克隆截图按标题/垂直领域蒸馏主色
3. 写出一份条目一份 md：Overview → Colors → Typography → Layout → Elevation & Depth → Shapes → Components → Do's and Don'ts
4. 用硬门槛审核：整文件不重复、How to use 不共用、YAML 与正文主色一致、克隆截图组不能共用一个 primary

本仓库 **不包含** 大型风格包或截图素材。把你的包放到任意目录，把 `--root` 指过去即可。

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

```
按 distill-design-md 审核这个风格包，再全量蒸馏 DESIGN.md
```

命令行（不经过 Agent 也可以）：

```bash
pip install -r requirements.txt
python3 scripts/audit_pack.py --root /path/to/pack
python3 scripts/distill_pack.py --root /path/to/pack
python3 scripts/audit_pack.py --root /path/to/pack
```

需要 Python 3.9+、Pillow、PyYAML。

包目录约定见 [SKILL.md](SKILL.md)。规范与门槛见 [references/spec.md](references/spec.md)、[references/quality-gates.md](references/quality-gates.md)。

## 最小自检

```bash
python3 scripts/make_mini_pack.py
python3 scripts/distill_pack.py --root examples/mini-pack
python3 scripts/audit_pack.py --root examples/mini-pack
```

应输出 `PASS`。`examples/mini-pack/` 是生成物，不要提交。

## 对外口径

蒸馏结果是 Agent 草稿：按公开可见的截图或 YAML 重建 token 与气质。不是官方品牌包，也不能当成可商用的完整设计系统。

## 许可

MIT。见 [LICENSE](LICENSE)。
