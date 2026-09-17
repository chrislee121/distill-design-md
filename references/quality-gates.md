# 质量门槛与克隆识别

打包或对外发布前跑 `python3 scripts/audit_pack.py --root <pack>`，必须全部 PASS。

## 硬门槛

| 门 | 通过条件 |
|---|---|
| 整文件 | 哈希互不相同，份数 = catalog 条目 |
| 导入指引 | `How to use` 最大重复 = 1 |
| YAML ↔ 正文 | `colors.primary` 与 Colors 节 `**primary**` 一致 |
| token | `{colors.x}` 都能在 YAML colors 里找到 |
| 八节 | 每份都有规范 8 个 `##` |
| 截图路径 | `screenshotPath` 指向真实文件（`brand-style-assets/by-id/` 或 `screenshots/by-id/`） |
| 垃圾注记 | 0 条 `Luxury gold` |
| 克隆截图 | 同一张图出现 ≥ 8 次时，这组的 primary **不能**只剩 1 种 |

## 按来源看「独立主色 / 条数」

远低于 1 就是套模板。经验阈值：

- Godly 独立截图：独立主色应 ≈ 条数（允许少量黑/白品牌）
- 克隆截图源（Motion Site 整组同一 hash）：独立主色必须 ≈ 条数（靠标题/垂直领域蒸馏）
- React Bits 演示台：禁止 200+ 条共用白字黑底
- GitHub 品牌分析若截图字节级相同：不要量化仓库页，应映射公开品牌 YAML（VoltAgent `awesome-design-md`）

`#000000` 出现十几次可以是合法的（Notion / Vercel / Cal / Geist）。先看是不是真黑品牌，再决定算不算克隆。

## 怎么发现「只换标题」

1. 对 `design-md/*.DESIGN.md` 做整文件 md5 — 全不同仍可能只是 id/URL 不同。
2. 抽掉 title / id / URL 后再哈希 How to use、Layout、主色。
3. 对截图做 md5：`n ≥ 8` 的组禁止共用一个 primary。
4. 按 `sourceSite` 统计 `primary` 种数。

典型假阳性：Motion Site 站点铬条蓝 `#1956B3`、GitHub 页灰绿 `#448F7A`、iOS 模板蓝 `#0A84FF`。这些是铬条，不是该风格的品牌色。

## 色板优先级（写文件时）

1. 上游已是 DESIGN.md 的 YAML（如 VoltAgent 品牌分析）→ 映射到默认 camelCase 键，不要抄整篇英文长文。
2. 公开品牌 / 设计系统 / shadcn 主题表。
3. 截图量化（独立文件）。过灰、过近背景、站点铬条 → 标弱。
4. 克隆截图：深浅画布可取自截图，**primary 必须按 slug/标题/垂直领域蒸馏**，HSL 用 slug 的 16-bit 哈希，避免 256 色相撞车。

## 截图量化注意

- 量化缩略图内侧 70%，降低导航铬条权重。
- 饱和度 `< 0.22` 的色不要当 primary。
- 暗画布贴在浅色文档页上时，暗块是舞台不是 CTA。
- 独立 App 截图不要因为「主色偏暗」就整组改成标题色相，否则 Godly 会从 ~860 种掉到 ~480 种。

## 蒸馏后抽查

至少打开这几类各一份对照截图：公开品牌、Godly App、克隆截图源、组件演示、shadcn 主题。确认主色不是站点皮肤，How to use 含该条 URL。
