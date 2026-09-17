# DESIGN.md 规范（蒸馏时用）

对齐 [Google Labs design.md](https://github.com/google-labs-code/design.md) `alpha`。默认导出用 camelCase 色键（与若干可视化编辑器的 `DESIGN.md` 导出对齐）。

输入可以是：公开网页 URL、本地 HTML、截图、名称/备注，或风格包 `catalog/entries.jsonl`。不要假定只有 jsonl。

## 文件结构

1. YAML front matter
2. Markdown 正文，出现的 `##` 必须按此顺序：

1. Overview
2. Colors
3. Typography
4. Layout
5. Elevation & Depth
6. Shapes
7. Components
8. Do's and Don'ts

YAML key 永远英文。正文中/英均可；本 skill 默认简体中文。

## 默认 YAML 色板键（camelCase）

必须写出这些键，组件只引用已存在的键：

```
primary secondary tertiary background surface
onPrimary onSecondary onTertiary onBackground onSurface
outline muted success warning error
```

禁止写 `colors.glass` / `colors.neutral` 却不在 `colors` 里定义。

## 字体 / 圆角 / 间距

typography 角色：`h1` `h2` `h3` `body` `label` `caption` `mono`  
每级：`fontFamily` `fontSize` `fontWeight` `lineHeight` `letterSpacing`

rounded：`sm` `md` `lg` `full`  
spacing：`xs` `sm` `md` `lg` `xl`

## 组件

至少：

```yaml
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.onPrimary}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.onSurface}"
    rounded: "{rounded.lg}"
    padding: "16px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.onSurface}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
```

引用语法：`{colors.primary}`、`{rounded.md}`。

## How to use

紧跟 Overview 段落后面一行：`How to use: …`  
必须含：**这条的名称、主色、正文字体、来源 URL**。禁止全包共用一句导入指引。

## 法律句

每份 Overview / description 写明：参考重建，非官方品牌资产；商标归原权利人。只还原公开可见的气质与 token。

## onPrimary

饱和主色上的按钮字：白字对比 ≥ 3.0 就用白（Airbnb `#FF385C`）。不要因为 WCAG 正文 4.5 略偏向黑，就把粉红按钮写成深灰字。
