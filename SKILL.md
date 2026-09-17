---
name: distill-design-md
description: Distills unique Google design.md alpha DESIGN.md files from a style catalog and screenshots, and audits packs for cloned templates. Use when the user asks to 蒸馏 DESIGN.md, 质量审核 DESIGN.md, 修复套模板/只换标题, regenerate a style pack's markdown, or prepare a DESIGN.md bundle for sale/export.
---

# 蒸馏 DESIGN.md

把「风格目录 + 截图」变成 **一份条目一份独立视觉合同**。禁止同一套稿只换标题、编号、链接。

规范细节读 [references/spec.md](references/spec.md)。门槛与克隆识别读 [references/quality-gates.md](references/quality-gates.md)。安装路径见 [references/runtimes.md](references/runtimes.md)。

本 skill 根目录记为 `$SKILL_ROOT`。

## 包形态

```
<pack>/
  catalog/entries.jsonl      # 每行一条，含 id/slug/title/sourceSite/screenshotPath
  brand-style-assets/by-id/  # 或 screenshots/by-id/
  design-md/*.DESIGN.md      # 写出目标
```

jsonl 至少要有：`id`、`slug`、`title`（或 `titleZh`）、`sourceSite`、`sourceUrl` 或 `originalSiteUrl`、`surface`、`screenshotPath`。

不要把体积很大的风格包（截图、成品 md）提交进本仓库。脚本只负责蒸馏与审核。

## 工作流

复制清单并逐项打勾：

```
- [ ] 1. 读规范 + 门槛
- [ ] 2. 审核现状（先证伪「已经独立」）
- [ ] 3. 给克隆截图分类，定色板来源
- [ ] 4. 蒸馏写回 design-md/
- [ ] 5. 再审核，抽查，未过则修提取器再跑
```

### 1. 读规范

先读 [references/spec.md](references/spec.md)。YAML 默认用 camelCase 色键（`onPrimary` 不是 `on-primary`）。八节顺序固定。

### 2. 审核

```bash
python3 $SKILL_ROOT/scripts/audit_pack.py --root <pack>
```

不要只看「文件哈希都不同」——把 id/URL 写进模板也会全不同。必须看：How to use 重复、按 `sourceSite` 的独立主色、截图 md5 克隆组。

### 3. 色板来源（按条，不要按站一套）

1. 上游已是 DESIGN.md（如 VoltAgent `designmd-*`）→ 映射 YAML，中文八节重写，**不要整篇英文粘贴**。
2. 公开品牌 / 设计系统 / shadcn 主题表。
3. **独立截图** → 内侧量化。过灰、铬条、暗块当 CTA → 弱。
4. **克隆截图**（同 hash ≥ 8）→ 画布可来自图，**primary 必须按 slug/标题/垂直领域蒸馏**。

GitHub 品牌分析截图经常是同一张仓库页：不要量化 GitHub 绿。有 `designmd-*` 时把 VoltAgent 克隆到包内缓存：

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/VoltAgent/awesome-design-md.git <pack>/scripts/cache/awesome-design-md
cd <pack>/scripts/cache/awesome-design-md && git sparse-checkout set design-md
```

### 4. 蒸馏

不要从零再写一个蒸馏器。跑：

```bash
python3 $SKILL_ROOT/scripts/distill_pack.py --root <pack>
```

依赖：`python3`、`Pillow`、`PyYAML`（见 [requirements.txt](requirements.txt)）。

正文必须按条目蒸馏：Layout / Components / Do's 用这条的 surface、标题类别、独特笔记；How to use 含 **名称 + 主色 + 字体 + URL**。

弱主色时：独立 App 截图仍优先量化（不要把整组独立截图改成标题色相）；演示台/克隆铬条才走标题 HSL（slug 用 16-bit 哈希，不要只用 1 个字节）。

饱和主色按钮：白字对比 ≥ 3.0 用白。

### 5. 再审核 + 抽查

再跑 `audit_pack.py`。失败则改提取启发式，**全量重跑**，不要手改几十份。

抽查：公开品牌、独立 App 截图、克隆截图源、组件演示、主题各一份，对照截图看主色。

## 对外口径

可以写：按 Google design.md alpha 蒸馏的 Agent 草稿；截图量化或公开 YAML 映射。

不要写：官方品牌包、人工逐套手写、可商用完整设计系统。

## 脚本

| 文件 | 用途 |
|---|---|
| [scripts/audit_pack.py](scripts/audit_pack.py) | 质量门槛，失败 exit 1 |
| [scripts/distill_pack.py](scripts/distill_pack.py) | 全量写出 DESIGN.md 并更新 catalog 路径/色注 |
| [scripts/make_mini_pack.py](scripts/make_mini_pack.py) | 生成 CI 用的最小示例包 |

在包根目录时可省略 `--root`（向上找 `catalog/entries.jsonl`）。
