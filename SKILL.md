---
name: distill-design-md
description: Distills unique Google design.md alpha DESIGN.md files from a webpage URL, screenshots, notes, or a style catalog. Identifies palette/type/shape then writes one visual contract per entry. Use when the user asks to 蒸馏 DESIGN.md, 识别风格, 从链接/截图生成 DESIGN.md, 质量审核, 修复套模板/只换标题, or prepare a DESIGN.md bundle.
---

# 蒸馏 DESIGN.md

把公开可见的风格信号变成 **一份条目一份独立视觉合同**。禁止同一套稿只换标题、编号、链接。

规范细节读 [references/spec.md](references/spec.md)。门槛与克隆识别读 [references/quality-gates.md](references/quality-gates.md)。安装路径见 [references/runtimes.md](references/runtimes.md)。

本 skill 根目录记为 `$SKILL_ROOT`。

## 两种入口

**单条**（网页链接 / 截图 / 备注）和 **风格包**（`catalog/entries.jsonl`）都能用。不要默认只走 jsonl。

| 用户给了什么 | 怎么做 |
|---|---|
| 网页链接 | 有浏览器就先截一张可见界面，再 `--url` + `--screenshot`；没截图也可以只抓 HTML/CSS |
| 截图（可多张） | `--screenshot` 可重复；画布和强调色以图为准 |
| 名称、气质、行业、深浅 | `--name` / `--notes` |
| 本地 HTML | `--html`（离线，不联网） |
| 现成风格包 | `distill_pack.py` + `audit_pack.py` |

至少要有 URL、HTML、截图、名称里的一样。链接 + 截图比只抓网页更准。

### 单条：识别再蒸馏

复制清单：

```
- [ ] 1. 收齐 URL / 截图 / 名称 / 备注
- [ ] 2. 有浏览器则打开链接，截可见界面（整页或首屏），不要只截浏览器铬条
- [ ] 3. 跑 distill_entry.py
- [ ] 4. 看识别 JSON：主色、字体、深浅、来源。不对就补截图或 notes 再跑
- [ ] 5. 打开写出的 DESIGN.md，对照截图抽查八节
```

```bash
python3 $SKILL_ROOT/scripts/distill_entry.py \
  --url https://example.com \
  --screenshot ./shot.png \
  --name "Example" \
  --notes "product, dense, light" \
  --out ./Example.DESIGN.md
```

只识别、先不写文件：

```bash
python3 $SKILL_ROOT/scripts/distill_entry.py --url https://example.com --screenshot ./shot.png --identify-only
```

`--url` 会向该站点发 HTTP 请求（页面 + 同主机少量 CSS；Google Fonts 链接只用来读字体名）。不要爬站内其它页面。用户没给链接时不要擅自抓。

色板优先级（单条）：

1. 能对上的公开品牌 / 主题表（主机或名称）
2. 网页 CSS 变量 / `theme-color`（主色）+ 截图（画布）
3. 截图内侧量化
4. 按名称 / URL 色相蒸馏（无可靠取色时）

正文仍走 Google design.md alpha：YAML camelCase + 固定八节。How to use 必须含 **名称 + 主色 + 字体 + URL**。

### 风格包：catalog + 每条截图

```
<pack>/
  catalog/entries.jsonl
  brand-style-assets/by-id/   # 或 screenshots/by-id/
  design-md/*.DESIGN.md
```

jsonl 至少要有：`id`、`slug`、`title`（或 `titleZh`）、`sourceSite`、`sourceUrl` 或 `originalSiteUrl`、`surface`、`screenshotPath`。

不要把体积很大的风格包提交进本仓库。

包工作流：

```
- [ ] 1. 读规范 + 门槛
- [ ] 2. 审核现状（先证伪「已经独立」）
- [ ] 3. 给克隆截图分类，定色板来源
- [ ] 4. 蒸馏写回 design-md/
- [ ] 5. 再审核，抽查，未过则修提取器再跑
```

```bash
python3 $SKILL_ROOT/scripts/audit_pack.py --root <pack>
python3 $SKILL_ROOT/scripts/distill_pack.py --root <pack>
python3 $SKILL_ROOT/scripts/audit_pack.py --root <pack>
```

依赖：`python3`、`Pillow`、`PyYAML`（见 [requirements.txt](requirements.txt)）。

包内色板：上游 DESIGN.md YAML → 公开品牌/主题表 → 独立截图量化 → 克隆截图（同 hash ≥ 8）按 slug/标题蒸馏主色。不要只看文件哈希——把 id/URL 写进模板也会全不同。

GitHub 品牌分析若截图是同一张仓库页：不要量化 GitHub 绿。有 `designmd-*` 时：

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/VoltAgent/awesome-design-md.git <pack>/scripts/cache/awesome-design-md
cd <pack>/scripts/cache/awesome-design-md && git sparse-checkout set design-md
```

弱主色时：独立 App 截图仍优先量化；演示台/克隆铬条才走标题 HSL（slug 用 16-bit 哈希）。饱和主色按钮：白字对比 ≥ 3.0 用白。

失败则改提取启发式并 **全量重跑**，不要手改几十份。抽查公开品牌、独立 App、克隆截图源、组件演示、主题各一份。

## 对外口径

可以写：按 Google design.md alpha 蒸馏的 Agent 草稿；截图量化、网页 CSS 或公开 YAML 映射。

不要写：官方品牌包、人工逐套手写、可商用完整设计系统。

## 脚本

| 文件 | 用途 |
|---|---|
| [scripts/distill_entry.py](scripts/distill_entry.py) | 单条：链接 / HTML / 截图 / 备注 → 识别 → 一份 DESIGN.md |
| [scripts/page_style.py](scripts/page_style.py) | 从公开网页抽取 CSS 变量、字体、圆角 |
| [scripts/audit_pack.py](scripts/audit_pack.py) | 风格包质量门槛，失败 exit 1 |
| [scripts/distill_pack.py](scripts/distill_pack.py) | 风格包全量写出 DESIGN.md |
| [scripts/make_mini_pack.py](scripts/make_mini_pack.py) | 生成 CI 用的最小示例包 |

在包根目录跑包脚本时可省略 `--root`（向上找 `catalog/entries.jsonl`）。
