#!/usr/bin/env python3
"""Distill each catalog entry into a unique, spec-compliant DESIGN.md.

Usage:
    python3 distill_pack.py --root /path/to/pack

Pack root must contain catalog/entries.jsonl and design-md/.
"""
from __future__ import annotations

import argparse
import colorsys
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path.cwd()
MD_DIR = ROOT / "design-md"
ASSET_DIR = ROOT / "brand-style-assets" / "by-id"
JSONL = ROOT / "catalog" / "entries.jsonl"
VOLT_ROOT = ROOT / "scripts" / "cache" / "awesome-design-md" / "design-md"


def configure(root: Path) -> None:
    global ROOT, MD_DIR, ASSET_DIR, JSONL, VOLT_ROOT
    ROOT = root.resolve()
    MD_DIR = ROOT / "design-md"
    for rel in ("brand-style-assets/by-id", "screenshots/by-id"):
        cand = ROOT / rel
        if cand.is_dir():
            ASSET_DIR = cand
            break
    else:
        ASSET_DIR = ROOT / "brand-style-assets" / "by-id"
    JSONL = ROOT / "catalog" / "entries.jsonl"
    VOLT_ROOT = ROOT / "scripts" / "cache" / "awesome-design-md" / "design-md"


def find_pack_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / "catalog" / "entries.jsonl").exists() and (p / "design-md").is_dir():
            return p
    raise SystemExit("找不到风格包根目录（需要 catalog/entries.jsonl 与 design-md/）")


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
LEGAL = (
    "参考重建，非官方品牌资产；商标归原权利人。"
    "只还原公开可见的气质与 token，不复制专有插画或指南原文。"
)

BRAND_COLORS = {
    "apple-hig": dict(primary="#007AFF", secondary="#8E8E93", tertiary="#34C759", background="#F2F2F7", surface="#FFFFFF"),
    "material-3": dict(primary="#6750A4", secondary="#625B71", tertiary="#7D5260", background="#FFFBFE", surface="#FFFFFF"),
    "ibm-carbon": dict(primary="#0F62FE", secondary="#393939", tertiary="#8D8D8D", background="#F4F4F4", surface="#FFFFFF"),
    "fluent-2": dict(primary="#0F6CBD", secondary="#616161", tertiary="#107C10", background="#F5F5F5", surface="#FFFFFF"),
    "shopify-polaris": dict(primary="#008060", secondary="#202223", tertiary="#5C5F62", background="#F6F6F7", surface="#FFFFFF"),
    "atlassian": dict(primary="#0052CC", secondary="#172B4D", tertiary="#6554C0", background="#F4F5F7", surface="#FFFFFF"),
    "github-primer": dict(primary="#0969DA", secondary="#24292F", tertiary="#1A7F37", background="#FFFFFF", surface="#F6F8FA"),
    "salesforce-lightning": dict(primary="#0176D3", secondary="#032D60", tertiary="#2E844A", background="#F3F3F3", surface="#FFFFFF"),
    "ant-design": dict(primary="#1677FF", secondary="#434343", tertiary="#52C41A", background="#F5F5F5", surface="#FFFFFF"),
    "stripe-brand": dict(primary="#635BFF", secondary="#0A2540", tertiary="#00D4FF", background="#FFFFFF", surface="#F6F9FC"),
    "linear": dict(primary="#5E6AD2", secondary="#8A8F98", tertiary="#EB5757", background="#0A0A0B", surface="#111214"),
    "vercel-geist": dict(primary="#000000", secondary="#666666", tertiary="#0070F3", background="#FFFFFF", surface="#FAFAFA"),
    "airbnb": dict(primary="#FF385C", secondary="#222222", tertiary="#00A699", background="#FFFFFF", surface="#F7F7F7"),
    "spotify": dict(primary="#1DB954", secondary="#FFFFFF", tertiary="#1ED760", background="#121212", surface="#181818"),
    "notion": dict(primary="#000000", secondary="#9B9A97", tertiary="#2383E2", background="#FFFFFF", surface="#F7F6F3"),
    "figma": dict(primary="#0D99FF", secondary="#1E1E1E", tertiary="#A259FF", background="#FFFFFF", surface="#F5F5F5"),
    "uber-base": dict(primary="#000000", secondary="#276EF1", tertiary="#05A357", background="#FFFFFF", surface="#F6F6F6"),
    "discord": dict(primary="#5865F2", secondary="#1E1F22", tertiary="#57F287", background="#313338", surface="#2B2D31"),
    "netflix-brand": dict(primary="#E50914", secondary="#FFFFFF", tertiary="#B81D13", background="#141414", surface="#000000"),
    "adobe-spectrum": dict(primary="#1473E6", secondary="#222222", tertiary="#268E6C", background="#F8F8F8", surface="#FFFFFF"),
    "shopify-hydrogen-storefront": dict(primary="#008060", secondary="#1A1A1A", tertiary="#D4A574", background="#FFFFFF", surface="#F7F4EF"),
    "microsoft-fluent-web": dict(primary="#0078D4", secondary="#605E5C", tertiary="#107C10", background="#FAF9F8", surface="#FFFFFF"),
    "cinematic-commerce": dict(primary="#C9A227", secondary="#E8DFD0", tertiary="#7A1F1F", background="#0B0B0C", surface="#141312"),
}

BRAND_TYPE = {
    "apple-hig": ("SF Pro Display", "SF Pro Text", "SF Pro Text"),
    "material-3": ("Roboto Flex", "Roboto", "Roboto Mono"),
    "ibm-carbon": ("IBM Plex Sans", "IBM Plex Sans", "IBM Plex Mono"),
    "fluent-2": ("Segoe UI Variable", "Segoe UI", "Cascadia Mono"),
    "shopify-polaris": ("Inter", "Inter", "SF Mono"),
    "atlassian": ("Atlassian Sans", "Inter", "JetBrains Mono"),
    "github-primer": ("Mona Sans", "Mona Sans", "MonoLisa"),
    "salesforce-lightning": ("Salesforce Sans", "Salesforce Sans", "Salesforce Mono"),
    "ant-design": ("Alibaba Sans", "Inter", "JetBrains Mono"),
    "stripe-brand": ("Sohne", "Inter", "Source Code Pro"),
    "linear": ("Inter Display", "Inter", "Berkeley Mono"),
    "vercel-geist": ("Geist", "Geist", "Geist Mono"),
    "airbnb": ("Cereal", "Cereal", "Roboto Mono"),
    "spotify": ("Circular Std", "Circular Std", "Spotify Mix"),
    "notion": ("Lyon Text", "Inter", "iA Writer Mono"),
    "figma": ("Whyte", "Inter", "Roboto Mono"),
    "uber-base": ("Uber Move", "Uber Move Text", "Uber Mono"),
    "discord": ("gg sans", "gg sans", "Source Code Pro"),
    "netflix-brand": ("Netflix Sans", "Netflix Sans", "Roboto Mono"),
    "adobe-spectrum": ("Adobe Clean", "Adobe Clean", "Source Code Pro"),
}

DS_COLORS = {
    "material-ui": dict(primary="#1976D2", secondary="#9C27B0", tertiary="#2E7D32", background="#FFFFFF", surface="#F5F5F5"),
    "daisyui": dict(primary="#570DF8", secondary="#F000B8", tertiary="#37CDBE", background="#FFFFFF", surface="#F2F2F2"),
    "chakra-ui": dict(primary="#319795", secondary="#2B6CB0", tertiary="#D69E2E", background="#FFFFFF", surface="#F7FAFC"),
    "primer-css": dict(primary="#0969DA", secondary="#24292F", tertiary="#1A7F37", background="#FFFFFF", surface="#F6F8FA"),
    "primer-react": dict(primary="#0969DA", secondary="#24292F", tertiary="#1A7F37", background="#FFFFFF", surface="#F6F8FA"),
    "hyperui": dict(primary="#4F46E5", secondary="#111827", tertiary="#10B981", background="#FFFFFF", surface="#F9FAFB"),
    "98-css": dict(primary="#000080", secondary="#C0C0C0", tertiary="#008080", background="#C0C0C0", surface="#DFDFDF"),
    "material-web": dict(primary="#6750A4", secondary="#625B71", tertiary="#7D5260", background="#FFFBFE", surface="#FFFFFF"),
    "base-ui": dict(primary="#000000", secondary="#666666", tertiary="#0070F3", background="#FFFFFF", surface="#FAFAFA"),
    "semi-design": dict(primary="#3BB346", secondary="#1C1F23", tertiary="#0077FA", background="#FFFFFF", surface="#F9F9F9"),
    "carbon": dict(primary="#0F62FE", secondary="#161616", tertiary="#8D8D8D", background="#F4F4F4", surface="#FFFFFF"),
    "flowbite": dict(primary="#3F83F8", secondary="#111827", tertiary="#0E9F6E", background="#FFFFFF", surface="#F9FAFB"),
    "grommet": dict(primary="#7D4CDB", secondary="#6FFFB0", tertiary="#FFCA58", background="#FFFFFF", surface="#F8F8F8"),
    "react95": dict(primary="#000080", secondary="#C3C7CB", tertiary="#008080", background="#C3C7CB", surface="#FFFFFF"),
    "reka-ui": dict(primary="#18181B", secondary="#71717A", tertiary="#3B82F6", background="#FAFAFA", surface="#FFFFFF"),
    "elastic-eui": dict(primary="#0077CC", secondary="#343741", tertiary="#00BFB3", background="#F5F7FA", surface="#FFFFFF"),
    "panda-css": dict(primary="#F6E05E", secondary="#1A202C", tertiary="#ED64A6", background="#FFFFFF", surface="#FFFFF0"),
    "skeleton": dict(primary="#0FBA81", secondary="#212121", tertiary="#818CF8", background="#FFFFFF", surface="#F8FAFC"),
    "arco-design": dict(primary="#165DFF", secondary="#1D2129", tertiary="#00B42A", background="#F7F8FA", surface="#FFFFFF"),
    "arco-design-vue": dict(primary="#165DFF", secondary="#1D2129", tertiary="#00B42A", background="#F7F8FA", surface="#FFFFFF"),
    "theme-ui": dict(primary="#07C", secondary="#111", tertiary="#E63E11", background="#FFFFFF", surface="#F6F6F6"),
    "ark-ui": dict(primary="#000000", secondary="#545454", tertiary="#3B82F6", background="#FFFFFF", surface="#FAFAFA"),
    "gluestack-ui": dict(primary="#0EA5E9", secondary="#1F2937", tertiary="#8B5CF6", background="#FFFFFF", surface="#F8FAFC"),
    "alibaba-fusion": dict(primary="#FF6A00", secondary="#333333", tertiary="#5584FF", background="#F2F3F5", surface="#FFFFFF"),
    "geist-ui": dict(primary="#000000", secondary="#666666", tertiary="#0070F3", background="#FFFFFF", surface="#FAFAFA"),
    "gestalt": dict(primary="#E60023", secondary="#111111", tertiary="#0A6252", background="#FFFFFF", surface="#F9F9F9"),
    "system-css": dict(primary="#000000", secondary="#DDDDDD", tertiary="#0000EE", background="#FFFFFF", surface="#FFFFFF"),
    "cloudscape": dict(primary="#0972D3", secondary="#16191F", tertiary="#037F0C", background="#FFFFFF", surface="#F2F3F3"),
    "ant-design-mobile": dict(primary="#1677FF", secondary="#333333", tertiary="#00B578", background="#FFFFFF", surface="#F5F5F5"),
    "element-plus": dict(primary="#409EFF", secondary="#303133", tertiary="#67C23A", background="#FFFFFF", surface="#F2F6FC"),
    "naive-ui": dict(primary="#18A058", secondary="#333639", tertiary="#2080F0", background="#FFFFFF", surface="#F5F5F5"),
    "vuetify": dict(primary="#1867C0", secondary="#5CBBF6", tertiary="#4CAF50", background="#FFFFFF", surface="#F5F5F5"),
    "radix-ui": dict(primary="#111111", secondary="#6F6F6F", tertiary="#3E63DD", background="#FFFFFF", surface="#F8F8F8"),
    "shadcn-ui": dict(primary="#18181B", secondary="#71717A", tertiary="#3B82F6", background="#FFFFFF", surface="#FAFAFA"),
    "mantine": dict(primary="#228BE6", secondary="#212529", tertiary="#12B886", background="#FFFFFF", surface="#F8F9FA"),
    "nextui-heroui": dict(primary="#006FEE", secondary="#7828C8", tertiary="#17C964", background="#FFFFFF", surface="#F4F4F5"),
    "headlessui": dict(primary="#0EA5E9", secondary="#0F172A", tertiary="#8B5CF6", background="#FFFFFF", surface="#F8FAFC"),
    "react-aria": dict(primary="#1473E6", secondary="#222222", tertiary="#268E6C", background="#F8F8F8", surface="#FFFFFF"),
    "spectrum-css": dict(primary="#1473E6", secondary="#222222", tertiary="#268E6C", background="#F8F8F8", surface="#FFFFFF"),
    "lightning-design-system": dict(primary="#0176D3", secondary="#032D60", tertiary="#2E844A", background="#F3F3F3", surface="#FFFFFF"),
    "blueprint": dict(primary="#2D72D2", secondary="#1C2127", tertiary="#238551", background="#F6F7F9", surface="#FFFFFF"),
    "fluentui": dict(primary="#0F6CBD", secondary="#242424", tertiary="#107C10", background="#FAF9F8", surface="#FFFFFF"),
    "paste": dict(primary="#0263E0", secondary="#121C2D", tertiary="#0D763D", background="#F4F4F6", surface="#FFFFFF"),
    "garden": dict(primary="#1F73B7", secondary="#2F3941", tertiary="#038153", background="#F8F9F9", surface="#FFFFFF"),
    "evergreen": dict(primary="#1070CA", secondary="#234361", tertiary="#47B881", background="#F9F9FB", surface="#FFFFFF"),
    "awesome-design-md": dict(primary="#111111", secondary="#666666", tertiary="#5E6AD2", background="#FFFFFF", surface="#FAFAFA"),
    "awesome-design-systems": dict(primary="#0969DA", secondary="#24292F", tertiary="#1A7F37", background="#FFFFFF", surface="#F6F8FA"),
    "style-dictionary": dict(primary="#FF9900", secondary="#232F3E", tertiary="#146EB4", background="#FFFFFF", surface="#F7F7F7"),
    "open-props": dict(primary="#0D47A1", secondary="#212121", tertiary="#00BCD4", background="#FFFFFF", surface="#F5F5F5"),
    "polaris": dict(primary="#008060", secondary="#202223", tertiary="#5C5F62", background="#F6F6F7", surface="#FFFFFF"),
    "quasar": dict(primary="#1976D2", secondary="#26A69A", tertiary="#9C27B0", background="#FFFFFF", surface="#F5F5F5"),
    "park-ui": dict(primary="#000000", secondary="#71717A", tertiary="#F97316", background="#FFFFFF", surface="#FAFAFA"),
    "zag-js": dict(primary="#000000", secondary="#545454", tertiary="#3B82F6", background="#FFFFFF", surface="#FAFAFA"),
    "protocol": dict(primary="#20123A", secondary="#4A4166", tertiary="#0060DF", background="#FFFFFF", surface="#F9F9FB"),
}

THEME_COLORS = {
    "vercel": dict(primary="#000000", secondary="#666666", tertiary="#0070F3", background="#FFFFFF", surface="#FAFAFA"),
    "modern-minimal": dict(primary="#18181B", secondary="#71717A", tertiary="#3B82F6", background="#FFFFFF", surface="#F4F4F5"),
    "zen-linen": dict(primary="#8B7355", secondary="#A89078", tertiary="#5C7A5C", background="#F5F0E8", surface="#FFFAF3"),
    "claude-amber": dict(primary="#D97757", secondary="#C96442", tertiary="#788C5D", background="#FAF9F5", surface="#FFFFFF"),
    "claude": dict(primary="#D97757", secondary="#5D4E37", tertiary="#2D2A26", background="#F5F0E8", surface="#FFFFFF"),
    "sage-garden": dict(primary="#4A7C59", secondary="#6B8F71", tertiary="#C4A35A", background="#F4F7F4", surface="#FFFFFF"),
    "lime-frost": dict(primary="#65A30D", secondary="#4D7C0F", tertiary="#A3E635", background="#F7FEE7", surface="#FFFFFF"),
    "elegant-luxury": dict(primary="#C9A227", secondary="#E8DFD0", tertiary="#7A1F1F", background="#1A1612", surface="#241E18"),
    "supabase": dict(primary="#3ECF8E", secondary="#FFFFFF", tertiary="#24B47E", background="#1C1C1C", surface="#292929"),
    "twitter": dict(primary="#1D9BF0", secondary="#71767B", tertiary="#00BA7C", background="#000000", surface="#16181C"),
    "catppuccin": dict(primary="#CBA6F7", secondary="#89B4FA", tertiary="#F38BA8", background="#1E1E2E", surface="#313244"),
    "vintage-paper": dict(primary="#8B4513", secondary="#5C4033", tertiary="#B87333", background="#F4E8C8", surface="#FFF8E7"),
    "solar-dusk": dict(primary="#EA580C", secondary="#FBBF24", tertiary="#FB7185", background="#1C1917", surface="#292524"),
    "t3-chat": dict(primary="#A855F7", secondary="#C084FC", tertiary="#22D3EE", background="#09090B", surface="#18181B"),
    "amber-slate": dict(primary="#F59E0B", secondary="#94A3B8", tertiary="#FBBF24", background="#0F172A", surface="#1E293B"),
    "graphite-mono": dict(primary="#A1A1AA", secondary="#71717A", tertiary="#E4E4E7", background="#18181B", surface="#27272A"),
    "indigo-mono": dict(primary="#818CF8", secondary="#A5B4FC", tertiary="#C7D2FE", background="#0B1020", surface="#151A2D"),
    "doom-64": dict(primary="#E8A838", secondary="#8B4513", tertiary="#DC2626", background="#1A120B", surface="#2A1C12"),
    "candyland": dict(primary="#F472B6", secondary="#FB7185", tertiary="#A78BFA", background="#FFF1F2", surface="#FFFFFF"),
    "ocean-breeze": dict(primary="#0EA5E9", secondary="#0369A1", tertiary="#22D3EE", background="#F0F9FF", surface="#FFFFFF"),
    "nature": dict(primary="#16A34A", secondary="#365314", tertiary="#84CC16", background="#F0FDF4", surface="#FFFFFF"),
    "amber-hearth": dict(primary="#D97706", secondary="#FBBF24", tertiary="#B45309", background="#1C1410", surface="#2A1E16"),
    "cyberpunk": dict(primary="#FF2E6D", secondary="#00F0FF", tertiary="#F5D90A", background="#0A0014", surface="#1A0030"),
    "azure-mono": dict(primary="#38BDF8", secondary="#7DD3FC", tertiary="#E0F2FE", background="#0C1222", surface="#151C2C"),
    "graphite": dict(primary="#52525B", secondary="#A1A1AA", tertiary="#18181B", background="#FAFAFA", surface="#FFFFFF"),
    "mono": dict(primary="#18181B", secondary="#71717A", tertiary="#000000", background="#FFFFFF", surface="#FAFAFA"),
    "claude-azure": dict(primary="#3B82F6", secondary="#1E3A5F", tertiary="#D97757", background="#F8FAFC", surface="#FFFFFF"),
    "neo-brutalism": dict(primary="#000000", secondary="#FACC15", tertiary="#EF4444", background="#FFFBEB", surface="#FFFFFF"),
    "kodama-grove": dict(primary="#3F6212", secondary="#65A30D", tertiary="#A8A29E", background="#F7FEE7", surface="#FFFFFF"),
    "mint-signal": dict(primary="#10B981", secondary="#047857", tertiary="#34D399", background="#ECFDF5", surface="#FFFFFF"),
    "clean-slate": dict(primary="#334155", secondary="#64748B", tertiary="#0EA5E9", background="#F8FAFC", surface="#FFFFFF"),
    "amber-minimal": dict(primary="#F59E0B", secondary="#B45309", tertiary="#78350F", background="#FFFBEB", surface="#FFFFFF"),
    "bubblegum": dict(primary="#EC4899", secondary="#F472B6", tertiary="#A855F7", background="#FDF2F8", surface="#FFFFFF"),
    "notebook": dict(primary="#1E293B", secondary="#64748B", tertiary="#2563EB", background="#FFFBEB", surface="#FFFFFF"),
    "sage-mist": dict(primary="#6B8F71", secondary="#A3B18A", tertiary="#588157", background="#F4F7F4", surface="#FFFFFF"),
    "retro-arcade": dict(primary="#F43F5E", secondary="#22D3EE", tertiary="#FBBF24", background="#0F0A1E", surface="#1A1030"),
    "perpetuity": dict(primary="#14B8A6", secondary="#5EEAD4", tertiary="#99F6E4", background="#042F2E", surface="#134E4A"),
    "violet-bloom": dict(primary="#8B5CF6", secondary="#A78BFA", tertiary="#EC4899", background="#FAF5FF", surface="#FFFFFF"),
    "amethyst-haze": dict(primary="#A78BFA", secondary="#C4B5FD", tertiary="#F0ABFC", background="#1E1B2E", surface="#2A2640"),
    "sunset-horizon": dict(primary="#F97316", secondary="#FB7185", tertiary="#FBBF24", background="#1C1410", surface="#2A1C14"),
    "darkmatter": dict(primary="#7C3AED", secondary="#22D3EE", tertiary="#E879F9", background="#030712", surface="#111827"),
    "whatsapp": dict(primary="#25D366", secondary="#00A884", tertiary="#53BDEB", background="#111B21", surface="#202C33"),
    "caffeine": dict(primary="#92400E", secondary="#B45309", tertiary="#44403C", background="#FFF7ED", surface="#FFFFFF"),
    "camel-linen": dict(primary="#B45309", secondary="#92400E", tertiary="#78716C", background="#FAF4EB", surface="#FFFBF5"),
    "northern-lights": dict(primary="#34D399", secondary="#22D3EE", tertiary="#A78BFA", background="#022C22", surface="#064E3B"),
    "tangerine": dict(primary="#F97316", secondary="#EA580C", tertiary="#0F172A", background="#FFF7ED", surface="#FFFFFF"),
    "mocha-mousse": dict(primary="#A16207", secondary="#D6B48A", tertiary="#7C2D12", background="#1C1410", surface="#2A2118"),
    "bold-tech": dict(primary="#2563EB", secondary="#22D3EE", tertiary="#F43F5E", background="#020617", surface="#0F172A"),
}

MOTIONSITE_VERTICAL = {
    "sty-1206": "3D AI 雕塑首屏",
    "sty-1207": "电商动能产品叙事",
    "sty-1208": "创意机构滚动剧场",
    "sty-1209": "玩味品牌动效",
    "sty-1210": "沉浸式 3D 空间品牌",
    "sty-1211": "SaaS 指标向前的深色界面",
    "sty-1212": "仪表盘旅程叙事",
    "sty-1213": "实验性漂移排版",
    "sty-1214": "工业制造清晰度",
    "sty-1215": "旅行电影感行程站",
    "sty-1216": "视频电商混合店面",
    "sty-1217": "互动贴纸游乐场",
    "sty-1218": "抽象 3D 哲学品牌",
    "sty-1219": "太空/天文营销",
    "sty-1220": "金融转化落地页",
    "sty-1221": "电动车发布美学",
    "sty-1222": "奢侈野兽派巨石品牌",
    "sty-1223": "厂牌复古-现代混搭",
    "sty-1224": "创意机构高饱和能量",
    "sty-1225": "时装编辑电商",
    "sty-1226": "增长工作室站点",
    "sty-1227": "3D 工作室作品集",
    "sty-1228": "医疗健康信任界面",
    "sty-1229": "社交身份产品站",
    "sty-1230": "设计工作室余烬光",
    "sty-1231": "科技纪元宣言页",
    "sty-1232": "DeFi 产品动效站",
    "sty-1233": "航天 B2B 落地页",
    "sty-1234": "工程顾问站点",
    "sty-1235": "探索旅行英雄区",
    "sty-1236": "高端地产营销",
    "sty-1237": "发光功能栅格 SaaS",
    "sty-1238": "安全产品硬化美学",
    "sty-1239": "AI 金融代理落地页",
    "sty-1240": "发光产品发布",
    "sty-1241": "IT 服务现代企业站",
    "sty-1242": "精品柔奢品牌",
    "sty-1243": "物流粗体工具界面",
    "sty-1244": "体育能量营销",
    "sty-1245": "生物科技信任色板",
    "sty-1246": "宇宙作品集视频底",
    "sty-1247": "电影感英雄提示风格",
    "sty-1248": "社区驱动 CTA 区块",
    "sty-1249": "金融河流动效品牌",
    "sty-1749": "转化导向的动画背景库",
}

VOLT_FOLDER = {
    "linear-app": "linear.app",
    "mistral-ai": "mistral.ai",
    "together-ai": "together.ai",
    "x-ai": "x.ai",
    "opencode-ai": "opencode.ai",
}

HUE_RULES = [
    (r"orange|ember|glow|sunset|tangerine|hearth|amber|solar", 28),
    (r"horse|camel|linen|paper|vintage|notebook", 32),
    (r"vertex|electric|veyra|azure|ocean|twitter", 198),
    (r"keel|agency|playful|idea", 48),
    (r"mind|ai|agent|claude|neural", 22),
    (r"haven|orbi|orbit|celest|nova|space|cosmic|aether|epoch", 258),
    (r"performance|metrics|saas|fin|defi|rivr|sellix|wise|coin", 162),
    (r"axle|journey|haul|logistics|cordex|industrial", 18),
    (r"drift|undr|experimental|cyber|neon", 312),
    (r"way.?far|travel|voyage|realty|zenith", 188),
    (r"video|ltx|cast|render|vinyl|music|spotify", 328),
    (r"sticker|candy|bubble|pink", 338),
    (r"alethia|abstract|persona|violet|amethyst|catppuccin", 278),
    (r"fashion|orla|shamoni|luxury|elegant", 348),
    (r"vitalis|medical|bio|nature|sage|mint|kodama", 148),
    (r"security|akor|doom", 8),
    (r"slam|sport|dunk|ferrari", 6),
    (r"community|cta|nexus|it ", 220),
    (r"background|shader|gradient|hero", 210),
    (r"mono|graphite|slate|clean", 220),
    (r"whatsapp|green|garden", 142),
    (r"coffee|caffeine|mocha|brown", 24),
]


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = str(h).strip().lstrip("#")
    if len(h) in (4, 8):
        h = h[:6] if len(h) == 8 else "".join(ch * 2 for ch in h[:3])
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) < 6 or not re.fullmatch(r"[0-9A-Fa-f]{6}", h[:6]):
        return (127, 127, 127)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*[max(0, min(255, int(x))) for x in rgb])


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))  # type: ignore[return-value]


def rel_lum(rgb: tuple[int, int, int]) -> float:
    def lin(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def sat(rgb: tuple[int, int, int]) -> float:
    r, g, b = [x / 255 for x in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    return 0.0 if mx == 0 else (mx - mn) / mx


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    l1, l2 = rel_lum(a), rel_lum(b)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def on_for(bg: tuple[int, int, int]) -> tuple[int, int, int]:
    light, dark = (250, 250, 250), (22, 22, 22)
    return light if contrast(light, bg) >= contrast(dark, bg) else dark


def ensure_aa(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> tuple[int, int, int]:
    if contrast(fg, bg) >= 4.5:
        return fg
    target = on_for(bg)
    cur = fg
    for _ in range(12):
        cur = mix(cur, target, 0.22)
        if contrast(cur, bg) >= 4.5:
            return cur
    return target


def hsl_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
    return int(r * 255), int(g * 255), int(b * 255)


def first_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    for sep in ("。", ". ", "；", "; "):
        if sep in text:
            return text.split(sep, 1)[0].strip()
    return text[:160]


def yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def dump_yaml(obj, indent=0) -> str:
    sp = "  " * indent
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            if isinstance(v, dict):
                lines.append(f"{sp}{k}:")
                lines.append(dump_yaml(v, indent + 1))
            elif isinstance(v, list):
                lines.append(f"{sp}{k}:")
                for item in v:
                    lines.append(f"{sp}  - {item}")
            elif isinstance(v, bool):
                lines.append(f"{sp}{k}: {'true' if v else 'false'}")
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                lines.append(f"{sp}{k}: {v}")
            else:
                lines.append(f'{sp}{k}: "{yaml_escape(str(v))}"')
        return "\n".join(lines)
    return f"{sp}{obj}"


def complete_colors(parts: dict[str, tuple[int, int, int]]) -> dict[str, tuple[int, int, int]]:
    primary = parts["primary"]
    background = parts.get("background") or (248, 247, 244)
    surface = parts.get("surface") or mix(background, on_for(background), 0.06)
    secondary = parts.get("secondary") or mix(primary, background, 0.35)
    tertiary = parts.get("tertiary") or mix(primary, (46, 125, 50), 0.35)
    on_bg = ensure_aa(parts.get("onBackground") or on_for(background), background)
    on_sf = ensure_aa(parts.get("onSurface") or on_for(surface), surface)
    white = (255, 255, 255)
    if parts.get("onPrimary"):
        on_pr = parts["onPrimary"]
        if contrast(on_pr, primary) < 3.0:
            on_pr = white if contrast(white, primary) >= 3.0 else ensure_aa(on_pr, primary)
    elif contrast(white, primary) >= 3.0 and sat(primary) >= 0.3:
        on_pr = white
    else:
        on_pr = ensure_aa(on_for(primary), primary)
    on_sc = ensure_aa(parts.get("onSecondary") or on_for(secondary), secondary)
    on_te = ensure_aa(parts.get("onTertiary") or on_for(tertiary), tertiary)
    return {
        "primary": primary,
        "secondary": secondary,
        "tertiary": tertiary,
        "background": background,
        "surface": surface,
        "onPrimary": on_pr,
        "onSecondary": on_sc,
        "onTertiary": on_te,
        "onBackground": on_bg,
        "onSurface": on_sf,
        "outline": parts.get("outline") or mix(surface, on_sf, 0.22),
        "muted": parts.get("muted") or mix(on_sf, surface, 0.42),
        "success": parts.get("success") or mix(muted_safe(on_sf, surface), (46, 160, 90), 0.55),
        "warning": parts.get("warning") or mix(primary, (200, 140, 40), 0.5),
        "error": parts.get("error") or mix(primary, (180, 40, 40), 0.5),
    }


def muted_safe(on_sf, surface):
    return mix(on_sf, surface, 0.42)


def from_named(named: dict[str, str]) -> dict[str, tuple[int, int, int]]:
    return complete_colors({k: hex_rgb(v) for k, v in named.items()})


def fallback_colors(seed: str) -> dict[str, tuple[int, int, int]]:
    h = hashlib.md5(seed.encode()).digest()
    primary = hsl_rgb(h[0] / 255 * 360, 0.55, 0.48)
    background = (248, 247, 244) if h[3] % 2 == 0 else (18, 18, 20)
    return complete_colors({"primary": primary, "background": background})


def keyword_hue(text: str, seed: str) -> float:
    blob = text.lower()
    digest = hashlib.md5(seed.encode()).digest()
    unique = int.from_bytes(digest[:2], "big") * 360 / 65535
    biased = None
    for pat, hue in HUE_RULES:
        if re.search(pat, blob):
            biased = hue
            break
    if biased is None:
        return unique
    return (0.62 * unique + 0.38 * biased) % 360


def name_palette(rec: dict, dark: bool | None = None) -> dict[str, tuple[int, int, int]]:
    seed = rec.get("slug") or rec["id"]
    text = " ".join(
        [
            rec.get("title") or "",
            rec.get("titleZh") or "",
            rec.get("paletteNotes") or "",
            rec.get("atmosphereHint") or "",
            " ".join(rec.get("styleTags") or []),
        ]
    )
    hue = keyword_hue(text, seed)
    if dark is None:
        dark = rec.get("sourceSite") in {"motionsite", "reactbits"} or "dark" in text.lower()
    digest = hashlib.md5(seed.encode()).digest()
    s = 0.52 + digest[2] / 255 * 0.22
    l = (0.46 + digest[3] / 255 * 0.14) if not dark else (0.54 + digest[4] / 255 * 0.12)
    primary = hsl_rgb(hue, s, l)
    if dark:
        background = hsl_rgb(hue, 0.18, 0.06)
        surface = hsl_rgb(hue, 0.16, 0.11)
        secondary = hsl_rgb((hue + 28) % 360, 0.22, 0.62)
        tertiary = hsl_rgb((hue + 140) % 360, 0.45, 0.52)
    else:
        background = hsl_rgb(hue, 0.08, 0.97)
        surface = (255, 255, 255)
        secondary = hsl_rgb((hue + 200) % 360, 0.12, 0.32)
        tertiary = hsl_rgb((hue + 48) % 360, 0.4, 0.42)
    return complete_colors(
        {
            "primary": primary,
            "secondary": secondary,
            "tertiary": tertiary,
            "background": background,
            "surface": surface,
        }
    )


CHROME = {hex_rgb("#1956B3"), hex_rgb("#448F7A"), hex_rgb("#0A84FF"), hex_rgb("#007AFF")}


def extract_from_image(path: Path) -> dict[str, tuple[int, int, int]] | None:
    try:
        im = Image.open(path)
        if getattr(im, "is_animated", False):
            im.seek(0)
        im = im.convert("RGBA").convert("RGB")
    except Exception:
        return None
    im.thumbnail((240, 240))
    q = im.quantize(colors=24, method=Image.Quantize.MEDIANCUT).convert("RGB")
    w, h = q.size
    inner = []
    for y in range(h):
        for x in range(w):
            c = q.getpixel((x, y))
            if 0.14 * h < y < 0.86 * h and 0.10 * w < x < 0.90 * w:
                inner.append(c)
    if not inner:
        inner = list(q.getdata())
    cnt = Counter(inner)
    total = sum(cnt.values()) or 1
    neutrals = sorted(cnt.items(), key=lambda kv: kv[1], reverse=True)
    background = neutrals[0][0]
    for c, _n in neutrals:
        if sat(c) < 0.18:
            background = c
            break

    def score(c: tuple[int, int, int], n: int) -> float:
        s = sat(c)
        if s < 0.16:
            return s * 0.05 * math.log(n + 1)
        if any(math.dist(c, chrome) < 18 for chrome in CHROME):
            return s * 0.15 * math.log(n + 1)
        if math.dist(c, background) < 22:
            return 0
        return (s**1.45) * math.log(n + 1) * (1 + abs(rel_lum(c) - rel_lum(background)))

    ranked = sorted(cnt.items(), key=lambda kv: score(kv[0], kv[1]), reverse=True)
    primary = None
    for c, n in ranked:
        if sat(c) >= 0.18 and n / total >= 0.002:
            primary = c
            break
    weak = False
    if primary is None:
        weak = True
        primary = ranked[0][0]
    if rel_lum(primary) < 0.16 and rel_lum(background) < 0.28:
        weak = True
    if abs(rel_lum(primary) - rel_lum(background)) < 0.08:
        weak = True
    if sat(primary) < 0.22:
        weak = True

    secondary = None
    for c, _n in ranked:
        if c == primary:
            continue
        if sat(c) >= 0.12 and math.dist(c, primary) > 28:
            secondary = c
            break
    tertiary = None
    for c, _n in ranked:
        if c in (primary, secondary, background):
            continue
        if sat(c) >= 0.2:
            tertiary = c
            break
    surface = background
    for c, _n in neutrals[1:10]:
        if math.dist(c, background) > 10:
            surface = c
            break
    if math.dist(surface, background) < 8:
        surface = mix(background, on_for(background), 0.07)
    out = complete_colors(
        {
            "primary": primary,
            "secondary": secondary or mix(primary, background, 0.4),
            "tertiary": tertiary or mix(primary, (46, 125, 50), 0.35),
            "background": background,
            "surface": surface,
        }
    )
    if weak:
        out["_weak"] = True  # type: ignore[index]
    return out


def apply_named(extracted: dict[str, tuple[int, int, int]], named: dict[str, str]) -> dict[str, tuple[int, int, int]]:
    out = dict(extracted)
    for k, hx in named.items():
        out[k] = hex_rgb(hx)
    return complete_colors(out)


def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    fm = text[4:end]
    for candidate in (
        fm,
        re.sub(
            r"^description:\s*(.+)$",
            lambda m: "description: " + json.dumps(m.group(1), ensure_ascii=False),
            fm,
            count=1,
            flags=re.M,
        ),
    ):
        try:
            data = yaml.safe_load(candidate)
            if isinstance(data, dict) and data.get("colors"):
                return data
        except Exception:
            continue
    colors = {}
    for m in re.finditer(r"^[ \t]*([A-Za-z0-9_-]+):\s*[\"']?(#[0-9A-Fa-f]{3,8})", fm, re.M):
        colors[m.group(1)] = m.group(2)
    if "primary" in colors:
        return {"colors": colors}
    return None


def hexes_from_markdown(text: str) -> list[str]:
    seen = []
    for hx in re.findall(r"#[0-9A-Fa-f]{6}", text):
        if hx.upper() not in {x.upper() for x in seen}:
            seen.append(hx)
    return seen


def pick_color(colors: dict, *names: str) -> str | None:
    lower = {str(k).lower(): v for k, v in colors.items()}
    for name in names:
        v = lower.get(name.lower())
        if isinstance(v, str) and "#" in v:
            return v
        if isinstance(v, str) and re.fullmatch(r"[0-9A-Fa-f]{6}", v):
            return "#" + v
    return None


def map_volt_colors(colors: dict, hexes: list[str]) -> dict[str, tuple[int, int, int]]:
    primary = pick_color(colors, "primary", "brand", "accent", "rausch") or (hexes[0] if hexes else "#3366CC")
    background = pick_color(colors, "canvas", "background", "bg", "page", "neutral") or "#FFFFFF"
    surface = pick_color(colors, "surface", "surface-card", "surface-1", "surface-soft", "surface-card", "canvas-soft") or background
    secondary = pick_color(colors, "ink", "secondary", "body", "ink-secondary", "brand-dark-900") or "#222222"
    tertiary = pick_color(colors, "tertiary", "plus", "luxe", "ruby", "success", "semantic-success") 
    if not tertiary:
        chromatic = [h for h in hexes if sat(hex_rgb(h)) >= 0.25 and hex_rgb(h) != hex_rgb(primary)]
        tertiary = chromatic[1] if len(chromatic) > 1 else chromatic[0] if chromatic else "#2E844A"
    muted = pick_color(colors, "muted", "ink-mute", "ink-subtle", "body-muted")
    outline = pick_color(colors, "hairline", "border", "outline", "hairline-soft")
    on_primary = pick_color(colors, "on-primary", "onPrimary", "on-dark")
    on_bg = pick_color(colors, "ink", "on-background", "onBackground", "body")
    parts = {
        "primary": hex_rgb(primary),
        "secondary": hex_rgb(secondary),
        "tertiary": hex_rgb(tertiary),
        "background": hex_rgb(background),
        "surface": hex_rgb(surface),
    }
    if muted:
        parts["muted"] = hex_rgb(muted)
    if outline:
        parts["outline"] = hex_rgb(outline)
    if on_primary:
        parts["onPrimary"] = hex_rgb(on_primary)
    if on_bg:
        parts["onBackground"] = hex_rgb(on_bg)
    return complete_colors(parts)


def norm_dim(v, default: str) -> str:
    if v is None:
        return default
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f"{int(v)}px"
    s = str(v).strip()
    return s or default


def font_name(v) -> str:
    if not v:
        return "Inter"
    s = str(v).split(",")[0].strip().strip("'\"")
    return s or "Inter"


def map_volt_type(typo: dict | None) -> tuple[str, str, str] | None:
    if not isinstance(typo, dict):
        return None
    roles = list(typo.values())
    dicts = [v for v in roles if isinstance(v, dict)]
    if not dicts:
        return None
    display = font_name(dicts[0].get("fontFamily"))
    body = display
    mono = "JetBrains Mono"
    for v in dicts:
        fam = font_name(v.get("fontFamily"))
        low = fam.lower()
        if "mono" in low or "code" in low:
            mono = fam
        elif "text" in low or "sans" in low:
            body = fam
    return display, body, mono


def map_volt_sizes(typo: dict | None, fallback: dict) -> dict:
    if not isinstance(typo, dict):
        return fallback
    dicts = [(k, v) for k, v in typo.items() if isinstance(v, dict) and v.get("fontSize")]
    if not dicts:
        return fallback

    def grab(*names, fallback=None):
        lower = {str(k).lower(): v for k, v in typo.items() if isinstance(v, dict)}
        for n in names:
            if n in lower:
                return lower[n]
        return fallback or dicts[-1][1]

    mapping = {
        "h1": grab("h1", "display-xl", "display-xxl", "display-lg", "display"),
        "h2": grab("h2", "display-md", "display-lg", "heading-lg", "headline"),
        "h3": grab("h3", "heading-md", "heading-sm", "title-md", "subhead"),
        "body": grab("body", "body-md", "body-lg", "body-sm"),
        "label": grab("label", "button", "button-md", "caption", "eyebrow"),
        "caption": grab("caption", "caption-sm", "micro", "body-sm"),
        "mono": grab("mono", "body-tabular", "micro", fallback=grab("body", "body-md")),
    }
    out = {}
    for role, tok in mapping.items():
        fb = fallback[role]
        ls = tok.get("letterSpacing")
        if ls is None or ls == "":
            ls = fb[3]
        elif isinstance(ls, (int, float)):
            ls = f"{ls}px" if ls else "0em"
        else:
            ls = str(ls)
        size = norm_dim(tok.get("fontSize"), fb[0])
        if role == "mono":
            num = re.match(r"(\d+)", size)
            if num and int(num.group(1)) > 14:
                size = "13px"
        out[role] = (
            size,
            int(tok.get("fontWeight") or fb[1]),
            float(tok.get("lineHeight") or fb[2]) if not isinstance(tok.get("lineHeight"), str) else fb[2],
            ls,
        )
    return out


def map_scale(block: dict | None, keys: list[str], fallback: dict[str, str]) -> dict[str, str]:
    if not isinstance(block, dict):
        return fallback
    lower = {str(k).lower(): v for k, v in block.items()}
    aliases = {
        "sm": ["sm", "s", "small"],
        "md": ["md", "m", "medium", "base"],
        "lg": ["lg", "l", "large"],
        "full": ["full", "pill", "xl"],
        "xs": ["xs", "xxs"],
        "xl": ["xl", "xxl", "huge", "section"],
    }
    out = dict(fallback)
    for key in keys:
        for a in aliases.get(key, [key]):
            if a in lower:
                out[key] = norm_dim(lower[a], fallback[key])
                break
    return out


def load_volt(slug: str) -> dict | None:
    if not slug.startswith("designmd-"):
        return None
    key = slug.replace("designmd-", "", 1)
    folder = VOLT_FOLDER.get(key, key)
    path = VOLT_ROOT / folder / "DESIGN.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    hexes = hexes_from_markdown(text)
    colors_src = (fm or {}).get("colors") if fm else None
    if not colors_src and hexes:
        colors_src = {"primary": hexes[0]}
    if not colors_src:
        return None
    colors = map_volt_colors(colors_src, hexes)
    desc = ""
    if fm and fm.get("description"):
        desc = str(fm["description"]).strip()
    elif text:
        desc = first_sentence(re.sub(r"^#.*\n", "", text))
    return {
        "colors": colors,
        "description": desc,
        "typography": (fm or {}).get("typography"),
        "rounded": (fm or {}).get("rounded"),
        "spacing": (fm or {}).get("spacing"),
        "components": list(((fm or {}).get("components") or {}).keys())[:8],
        "folder": folder,
    }


def find_asset(eid: str) -> Path | None:
    hits = list(ASSET_DIR.glob(f"{eid}.*"))
    return hits[0] if hits else None


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def pick_type(rec: dict) -> tuple[str, str, str]:
    override = rec.get("fontFamilies")
    if isinstance(override, (list, tuple)) and len(override) >= 3:
        return str(override[0]), str(override[1]), str(override[2])
    slug = rec.get("slug") or ""
    if slug in BRAND_TYPE:
        return BRAND_TYPE[slug]
    tags = " ".join(rec.get("styleTags") or []).lower()
    surface = rec.get("surface") or ""
    site = rec.get("sourceSite") or ""
    if surface == "mobile-app" or "ios-android" in tags:
        return ("SF Pro Display", "SF Pro Text", "SF Pro Text")
    if "serif" in tags or "editorial" in tags:
        return ("Source Serif 4", "Source Serif 4", "IBM Plex Mono")
    if site == "vercel" or "geist" in tags or "mono" in tags:
        return ("Geist", "Geist", "Geist Mono")
    if site == "reactbits":
        return ("Inter", "Inter", "JetBrains Mono")
    if site == "21st" and "theme" in slug:
        return ("Geist", "Geist", "Geist Mono")
    if site == "github":
        return ("Mona Sans", "Inter", "JetBrains Mono")
    if site == "motionsite":
        return ("Inter Display", "Inter", "Space Grotesk")
    if rec.get("sourceType") == "design-system":
        return ("Inter", "Inter", "IBM Plex Mono")
    return ("Inter Display", "Inter", "JetBrains Mono")


def type_sizes(rec: dict) -> dict[str, tuple[str, int, float, str]]:
    surface = rec.get("surface") or ""
    site = rec.get("sourceSite") or ""
    if surface == "mobile-app":
        return {
            "h1": ("34px", 700, 1.15, "0.01em"),
            "h2": ("22px", 600, 1.25, "0em"),
            "h3": ("17px", 600, 1.3, "0em"),
            "body": ("15px", 400, 1.4, "0em"),
            "label": ("13px", 600, 1.25, "0.04em"),
            "caption": ("12px", 400, 1.3, "0.02em"),
            "mono": ("12px", 400, 1.35, "0em"),
        }
    if site == "reactbits":
        return {
            "h1": ("28px", 600, 1.2, "-0.02em"),
            "h2": ("18px", 600, 1.3, "-0.01em"),
            "h3": ("15px", 500, 1.35, "0em"),
            "body": ("14px", 400, 1.5, "0em"),
            "label": ("12px", 500, 1.3, "0.06em"),
            "caption": ("11px", 400, 1.35, "0.04em"),
            "mono": ("12px", 400, 1.4, "0em"),
        }
    if rec.get("sourceType") == "design-system":
        return {
            "h1": ("40px", 600, 1.15, "-0.02em"),
            "h2": ("24px", 600, 1.25, "-0.01em"),
            "h3": ("18px", 600, 1.3, "0em"),
            "body": ("16px", 400, 1.5, "0em"),
            "label": ("12px", 500, 1.3, "0.06em"),
            "caption": ("12px", 400, 1.4, "0.02em"),
            "mono": ("13px", 400, 1.45, "0em"),
        }
    return {
        "h1": ("48px", 600, 1.1, "-0.03em"),
        "h2": ("28px", 600, 1.2, "-0.02em"),
        "h3": ("20px", 600, 1.3, "-0.01em"),
        "body": ("16px", 400, 1.5, "0em"),
        "label": ("13px", 500, 1.3, "0.04em"),
        "caption": ("12px", 400, 1.4, "0.02em"),
        "mono": ("13px", 400, 1.45, "0em"),
    }


def radii_spacing(rec: dict) -> tuple[dict[str, str], dict[str, str]]:
    mat = (rec.get("materialHint") or "").lower()
    if "clay" in mat or "neu" in mat:
        r = {"sm": "14px", "md": "22px", "lg": "32px", "full": "9999px"}
    elif "hairline" in mat:
        r = {"sm": "4px", "md": "8px", "lg": "12px", "full": "9999px"}
    elif "glass" in mat or "liquid" in mat:
        r = {"sm": "10px", "md": "16px", "lg": "24px", "full": "9999px"}
    elif "paper" in mat:
        r = {"sm": "6px", "md": "10px", "lg": "16px", "full": "9999px"}
    elif "flat" in mat or rec.get("sourceType") == "design-system":
        r = {"sm": "6px", "md": "10px", "lg": "14px", "full": "9999px"}
    else:
        r = {"sm": "8px", "md": "12px", "lg": "20px", "full": "9999px"}
    if rec.get("surface") == "mobile-app":
        s = {"xs": "4px", "sm": "8px", "md": "16px", "lg": "24px", "xl": "32px"}
    elif rec.get("sourceSite") == "reactbits":
        s = {"xs": "4px", "sm": "8px", "md": "12px", "lg": "20px", "xl": "32px"}
    else:
        s = {"xs": "4px", "sm": "8px", "md": "16px", "lg": "24px", "xl": "40px"}
    return r, s


def elevation_recipe(rec: dict) -> tuple[str, str, str, str]:
    mat = rec.get("materialHint") or "flat"
    ml = mat.lower()
    if "glass" in ml or "liquid" in ml:
        return (
            "none",
            "0 8px 32px color-mix(in srgb, var(--foreground) 8%, transparent)",
            "0 24px 64px color-mix(in srgb, var(--foreground) 14%, transparent)",
            "深度靠 backdrop-filter 与层叠，不要用厚投影冒充玻璃。",
        )
    if "clay" in ml or "neu" in ml:
        return (
            "4px 4px 8px rgba(0,0,0,.12), -4px -4px 8px rgba(255,255,255,.6)",
            "6px 6px 14px rgba(0,0,0,.14), -6px -6px 14px rgba(255,255,255,.7)",
            "inset 4px 4px 8px rgba(0,0,0,.12)",
            "凸起用双阴影，按下/输入用内阴影；表面色必须贴近背景。",
        )
    if "hairline" in ml:
        return ("none", "none", "none", "层级用 1px 细分隔，不用卡片投影。")
    if rec.get("surface") == "mobile-app":
        return (
            "0 1px 0 rgba(0,0,0,.04)",
            "0 8px 24px rgba(0,0,0,.08)",
            "0 16px 40px rgba(0,0,0,.12)",
            "iOS 分组列表用系统材质，避免 Android 式色调海拔堆叠。",
        )
    if rec.get("sourceSite") == "motionsite":
        return (
            "none",
            "0 24px 80px color-mix(in srgb, var(--foreground) 18%, transparent)",
            "0 40px 120px color-mix(in srgb, var(--foreground) 28%, transparent)",
            "电影感来自全幅视频/3D，不是卡片投影。静态层保持可读。",
        )
    return (
        "0 1px 2px rgba(15,23,42,.06)",
        "0 8px 24px rgba(15,23,42,.08)",
        "0 20px 48px rgba(15,23,42,.12)",
        "阴影带一点背景色相；高密度界面可用细分隔替代卡片。",
    )


def unique_layout(rec: dict, note: str) -> str:
    title = rec.get("titleZh") or rec.get("title") or rec["id"]
    surface = rec.get("surface") or ""
    t = title.lower()
    if rec.get("sourceSite") == "github" and str(rec.get("slug") or "").startswith("designmd-"):
        brand = title.replace(" DESIGN.md analysis", "").strip()
        return (
            f"「{title}」按 {brand} 公开站点信息架构还原：顶栏品牌 + 首屏主张 + 产品证明。"
            f"{(' 观察：' + note + '。') if note else ''} 不要做成 GitHub README 排版。"
        )
    if rec.get("sourceSite") == "github":
        return (
            f"「{title}」按组件库文档还原：侧栏目录、内容列、示例画布。"
            f"{(' ' + note + '。') if note else ''} 间距走 spacing 刻度，不要营销首屏堆叠。"
        )
    if rec.get("sourceSite") == "motionsite":
        vertical = MOTIONSITE_VERTICAL.get(rec["id"]) or note
        return (
            f"「{title}」是动效营销站，垂直方向是{vertical}。"
            "结构：粘性导航、首屏视频或 3D、bento/社会证明、页脚跑马灯。"
            "小于 768px 单列；静态文案对比度不能靠动画补。"
        )
    if rec.get("sourceSite") == "21st" and "theme" in (rec.get("slug") or ""):
        return (
            f"「{title}」是 shadcn 主题种子：button / card / input / dialog 共用同一套色与半径。"
            f"{(' 气质：' + note + '。') if note else ''} 先定 tokens 再铺页面，不要另开一套主色。"
        )
    if rec.get("sourceSite") == "reactbits":
        bit = (rec.get("slug") or title).split("-")[-1]
        return (
            f"「{title}」是 React Bits 单效果舞台：深色画布上只演示 `{bit}`。"
            "铬件贴边或悬浮，不要挡住运动主体，也不要铺成 SaaS 官网。"
        )
    if surface == "mobile-app":
        extra = "主内容 + 底栏 Tab，触控热区 ≥ 44pt，尊重 Safe Area。"
        if re.search(r"calc|计算", t):
            extra = "结果区在上、数字键盘在下，单手可达。"
        elif re.search(r"weather|天气", t):
            extra = "当前天气大字号，下方小时/周预报。"
        elif re.search(r"music|spotify|播客|电台", t):
            extra = "封面/播放条固定底部，列表可滚。"
        elif re.search(r"fit|gym|health|健康|健身", t):
            extra = "今日环/指标卡片在上，活动列表在下。"
        elif re.search(r"chat|message|inbox|邮件", t):
            extra = "会话列表或线程，底栏输入，顶栏标题。"
        elif re.search(r"map|maps|导航", t):
            extra = "全幅地图，底部抽屉放地点详情。"
        elif re.search(r"shop|store|commerce|购物", t):
            extra = "商品网格 + 底栏购物车，详情用大图。"
        elif re.search(r"bank|wallet|pay|支付|银行", t):
            extra = "余额卡片 + 流水列表，操作收在主按钮。"
        return f"「{title}」是 App Store 截图参考。{extra} 还原时走 iOS 大标题/分组列表，不要做成营销落地页。"
    if rec.get("sourceType") == "design-system":
        if rec.get("slug") == "apple-hig":
            return "「苹果人机界面指南」按 iOS 文档习惯还原：侧栏目录 + 内容列，控件用连续圆角与系统蓝。触控 ≥ 44pt，尊重 Safe Area 与 Dynamic Type。"
        return f"「{title}」按设计系统文档信息架构还原：侧栏或顶栏导航 + 内容列。间距用本文 spacing 刻度。"
    if rec.get("sourceSite") == "21st":
        return (
            f"「{title}」是多区块模板：导航、首屏、功能、定价或后台。"
            f"{(' ' + note + '。') if note else ''} 按截图节奏分节，不要把所有区块做成同一张卡片。"
        )
    if surface == "product-admin":
        return f"「{title}」是后台/产品壳：顶栏 + 侧栏 + 主表。密度高于营销站，对齐用 8px。"
    if note:
        return f"「{title}」布局要点：{note}。小于 768px 单列，容器约 1120–1400px。"
    return f"「{title}」是营销首页：首屏主张、证明、功能、页脚。小于 768px 单列，容器宽度约 1120–1400px。"


def unique_motion(rec: dict) -> str:
    title = rec.get("titleZh") or rec.get("title")
    notes = first_sentence(rec.get("motionNotes") or "")
    cloned = notes in {
        "Mobile native transitions; tab/bar micro-interactions",
        "Brand-typical marketing/product motion; reconstruct, don't copy assets",
        "Section reveals + component hover states typical of modern React templates",
        "Likely scroll/entrance polish typical of Godly picks",
        "Continuous shader loops; keep UI static",
        "As documented in community DESIGN.md analyses — reconstruct only",
        "Standard shadcn transitions; theme mainly color/radius/font",
        "Scroll-pinned sections, GSAP/Framer-style timelines, video backgrounds",
    }
    if rec.get("surface") == "mobile-app":
        return f"「{title}」动效克制：推入/淡出 200–300ms，Tab 切换不要弹跳。尊重 Reduce Motion。"
    if rec.get("sourceSite") == "reactbits":
        return f"「{title}」的英雄是循环着色器或指针交互；周围按钮保持静态，避免再套一层页面转场。"
    if rec.get("sourceSite") == "motionsite":
        return f"「{title}」允许滚动驱动与时间轴，但 `{title}` 的正文对比度不能靠动画补。尊重 Reduce Motion。"
    if notes and not cloned:
        return f"「{title}」动效：{notes}。只重建节奏，不复制专有资源。"
    return f"「{title}」默认 CSS 过渡 180–280ms，ease-out。不要上全屏过场。"


def unique_components(rec: dict, colors: dict[str, str], extra_names: list[str] | None = None) -> str:
    title = rec.get("titleZh") or rec.get("title")
    surface = rec.get("surface") or ""
    tags = ", ".join(rec.get("styleTags") or []) or "无额外标签"
    extra = ""
    if extra_names:
        extra = "优先落地：" + "、".join(f"`{n}`" for n in extra_names[:5]) + "。\n"
    if surface == "mobile-app":
        return (
            extra
            + f"- **按钮**：主按钮 `{colors['primary']}` 胶囊，宽度足够拇指点击。适用于「{title}」。\n"
            f"- **列表**：分组行 + 细分隔；不要用 Web 卡片网格冒充 App。\n"
            f"- **导航**：底栏最多 5 项；选中态只用 primary。\n"
            f"- **输入**：浅填充井。标签：{tags}。"
        )
    if rec.get("sourceSite") == "reactbits":
        return (
            extra
            + f"- **舞台**：全幅效果层，背景 `{colors['background']}`，不要挡住「{title}」的运动主体。\n"
            f"- **按钮 / 卡片**：演示壳跟 YAML，不要再套 Tailwind 默认蓝。\n"
            f"- **标签**：{tags}。"
        )
    if rec.get("sourceType") == "design-system" or str(rec.get("slug") or "").startswith("gh-ds-"):
        return (
            extra
            + f"- **按钮**：主、次、幽灵三档，主色 `{colors['primary']}` 稀缺。\n"
            f"- **卡片 / 输入**：`{colors['surface']}` + outline，圆角跟 rounded.md。\n"
            f"- **文档页**：示例区与 token 表分开，避免把「{title}」做成一张大海报。\n"
            f"- **标签**：{tags}。"
        )
    return (
        extra
        + f"- **导航**：字重清楚，CTA 只用一个 `{colors['primary']}`。\n"
        f"- **首屏**：标题 / 副文 / 主按钮分层，叠在影像上必须过 AA。\n"
        f"- **卡片**：「{title}」的证明/功能区用 `{colors['surface']}`，避免每块都描边。\n"
        f"- **标签**：{tags}。"
    )


def unique_dos(rec: dict, colors: dict[str, str]) -> tuple[list[str], list[str]]:
    title = rec.get("titleZh") or rec.get("title")
    mat = rec.get("materialHint") or "flat"
    dos = [
        f"主色只用 `{colors['primary']}`，不要再引入第二条品牌色。",
        f"正文写在 `{colors['onBackground']}` / `{colors['background']}` 配对上，先过 AA。",
        f"还原「{title}」时先对齐截图 `brand-style-assets/by-id/{rec['id']}`，再改细节。",
    ]
    donts = [
        "不要声称这是官方品牌资产或可商用的完整设计系统。",
        "不要把本文件的 token 和另一套风格混进同一界面。",
        f"不要忽略材质提示：{first_sentence(mat) or mat}。",
    ]
    if rec.get("surface") == "mobile-app":
        dos.append("触控目标 ≥ 44pt，图标按 SF Symbols 语义落地。")
        donts.append("不要用 Material 色调海拔或 Web 顶栏冒充 iOS。")
    if "glass" in mat.lower() or "liquid" in mat.lower():
        donts.append("不要用实心色块冒充玻璃：要有 backdrop-filter 和可透视背景。")
    if rec.get("sourceSite") == "reactbits":
        donts.append("不要把演示舞台铺成完整 SaaS 官网。")
    if rec.get("sourceSite") == "motionsite":
        donts.append("不要把 Motion Site 站点铬条（蓝导航）当成这一页的品牌色。")
    if str(rec.get("slug") or "").startswith("designmd-"):
        donts.append("不要把 GitHub 仓库页的绿/灰当成品牌色。")
    return dos, donts


def resolve_palette(rec: dict, shot: Path, cloned: bool) -> tuple[dict[str, tuple[int, int, int]], str, dict]:
    slug = rec.get("slug") or ""
    extra: dict = {}
    volt = load_volt(slug)
    if volt:
        extra = volt
        extra["origin"] = "voltagent"
        return volt["colors"], "VoltAgent 公开品牌分析 YAML（映射到本产品 token 键）", extra

    theme_key = ""
    if slug.startswith("21st-theme-"):
        theme_key = slug.replace("21st-theme-", "")
    if theme_key in THEME_COLORS:
        return from_named(THEME_COLORS[theme_key]), f"shadcn/tweakcn 主题「{theme_key}」公开色", extra

    ds_key = slug.replace("gh-ds-", "") if slug.startswith("gh-ds-") else slug
    if ds_key in DS_COLORS:
        return from_named(DS_COLORS[ds_key]), "该组件库公开主色", extra
    if slug in BRAND_COLORS:
        extracted = extract_from_image(shot) or fallback_colors(slug)
        extracted.pop("_weak", None)
        return apply_named(extracted, BRAND_COLORS[slug]), "公开品牌主色叠在截图表面上", extra

    if rec.get("sourceSite") == "reactbits":
        extracted = None if cloned else extract_from_image(shot)
        named = name_palette(rec, dark=True)
        if extracted:
            extracted.pop("_weak", None)
            stage = extracted["background"]
            if rel_lum(extracted["primary"]) < rel_lum(stage):
                stage = extracted["primary"]
            if rel_lum(stage) < 0.35:
                named["background"] = stage
                named["surface"] = mix(stage, (255, 255, 255), 0.08)
                named = complete_colors(named)
        return named, "React Bits 演示台：深色舞台取截图，强调色按组件名蒸馏", extra

    extracted = None if cloned else extract_from_image(shot)
    if cloned or extracted is None or extracted.pop("_weak", False):
        dark = rec.get("sourceSite") in {"motionsite", "reactbits"} or (
            extracted is not None and rel_lum(extracted["background"]) < 0.35
        )
        named = name_palette(rec, dark=dark)
        if extracted and not cloned:
            named["background"] = extracted["background"]
            named["surface"] = extracted["surface"]
            named["onBackground"] = extracted["onBackground"]
            named["onSurface"] = extracted["onSurface"]
            named = complete_colors(named)
        why = "截图与多条复用同一张铬条，主色按条目标题/垂直领域蒸馏" if cloned else "截图偏中性灰，主色按条目标题色相蒸馏"
        return named, why, extra

    return extracted, f"截图 `{shot.name}` 量化（排除站点铬条）", extra


def build_md(
    rec: dict,
    colors_rgb: dict[str, tuple[int, int, int]],
    shot_name: str,
    origin: str,
    extra: dict,
) -> str:
    colors = {k: rgb_hex(v) for k, v in colors_rgb.items() if not str(k).startswith("_")}
    title = rec.get("titleZh") or rec.get("title") or rec["id"]
    slug = rec.get("slug") or rec["id"]
    display, body_font, mono = pick_type(rec)
    volt_type = map_volt_type(extra.get("typography"))
    if volt_type:
        display, body_font, mono = volt_type
    sizes = map_volt_sizes(extra.get("typography"), type_sizes(rec))
    rounded, spacing = radii_spacing(rec)
    rounded = map_scale(extra.get("rounded"), ["sm", "md", "lg", "full"], rounded)
    spacing = map_scale(extra.get("spacing"), ["xs", "sm", "md", "lg", "xl"], spacing)
    sm, md, lg, elev_note = elevation_recipe(rec)
    url = rec.get("originalSiteUrl") or rec.get("sourceUrl") or ""
    mat = rec.get("materialHint") or "flat"
    atm = rec.get("atmosphereHint") or ""
    note = ""
    if extra.get("description"):
        note = first_sentence(extra["description"])
    elif rec["id"] in MOTIONSITE_VERTICAL:
        note = MOTIONSITE_VERTICAL[rec["id"]]
    else:
        raw = first_sentence(rec.get("layoutNotes") or "")
        cloned_layout = raw in {
            "Phone-framed screenshot stacks, iconography, onboarding flows",
            "Multi-section template: nav, hero, features, pricing/CTA or admin layout",
            "Marketing + product chrome patterns summarized for agent import",
            "Hero-forward marketing with product proof sections (Godly-curated)",
            "Hero video/3D, sticky nav, bento/proof, marquee footer — prompt-library structure",
            "Theme applies across primitives: button, card, input, dialog",
            "Observed docs sidebar.",
            "Component library / token architecture; storybook-like composition",
        }
        if raw and not cloned_layout:
            note = raw
    cloned_atm = atm.startswith("21st.dev template") or atm.startswith("App Store") or atm.startswith("Agent-oriented") or atm.startswith("Premium AI-prompted")
    dark = rel_lum(colors_rgb["background"]) < 0.35
    mode = "深色" if dark else "浅色"
    overview = (
        f"{title}（`{slug}`）是给 coding agent 用的视觉合同。界面按{mode}还原，"
        f"主色 `{colors['primary']}`，背景 `{colors['background']}`，标题字体 {display}。"
        f"{('气质：' + first_sentence(atm) + '。') if atm and not cloned_atm else ''}"
        f"{('分析要点：' + note + '。') if note and 'Luxury gold' not in note and 'generic' not in note.lower() else ''}"
        f"{LEGAL}"
    )
    how = (
        f"把本文件放到仓库根目录，并写明：写界面前先读 DESIGN.md；"
        f"「{title}」颜色以 `{colors['primary']}` 为准，正文字体用 {body_font}。"
        f"来源 {url or '见 catalog'}。"
    )
    color_lines = "\n".join(f"- **{k}** (`{v}`)" for k, v in colors.items())
    type_yaml = {}
    type_lines = []
    for role, (size, weight, lh, track) in sizes.items():
        fam = mono if role == "mono" else (display if role == "h1" else body_font)
        type_yaml[role] = {
            "fontFamily": fam,
            "fontSize": size,
            "fontWeight": weight,
            "lineHeight": lh,
            "letterSpacing": track,
        }
        type_lines.append(f"- **{role}**: {fam} {weight} / {size} / {lh} / {track}")
    dos, donts = unique_dos(rec, colors)
    fm = {
        "version": "alpha",
        "name": title,
        "description": f"{title} — {LEGAL}",
        "colors": colors,
        "typography": type_yaml,
        "rounded": rounded,
        "spacing": spacing,
        "components": {
            "button-primary": {
                "backgroundColor": "{colors.primary}",
                "textColor": "{colors.onPrimary}",
                "rounded": "{rounded.md}",
                "padding": "10px 16px",
            },
            "card": {
                "backgroundColor": "{colors.surface}",
                "textColor": "{colors.onSurface}",
                "rounded": "{rounded.lg}",
                "padding": "16px",
            },
            "input": {
                "backgroundColor": "{colors.surface}",
                "textColor": "{colors.onSurface}",
                "rounded": "{rounded.sm}",
                "padding": "8px 12px",
            },
        },
    }
    layout = unique_layout(rec, note)
    platform = (
        "iOS：触控 ≥ 44pt，Safe Area，SF Symbols，大标题/分组列表。"
        if rec.get("surface") == "mobile-app"
        else "Web：移动优先，<768px 单列，正文 ≥ 16px，容器约 1120–1400px。"
    )
    md = f"""---
{dump_yaml(fm)}
---

# {title}

## Overview

{overview}

How to use: {how}

## Colors

语义色来源：{origin}。单强调色，不要再开一条品牌色。

{color_lines}

## Typography

层级靠字号和字重，不靠全大写喊话。行宽大约 65 字。

{chr(10).join(type_lines)}

## Layout

间距刻度：{', '.join(f'{k}={v}' for k, v in spacing.items())}。

{platform}

{layout}

## Elevation & Depth

- sm: `{sm}`
- md: `{md}`
- lg: `{lg}`
- material: {mat}
- {elev_note}

{unique_motion(rec)}

## Shapes

圆角刻度：{', '.join(f'{k}={v}' for k, v in rounded.items())}。按钮可用 `rounded.full` 胶囊；卡片用 `rounded.lg`。

## Components

{unique_components(rec, colors, extra.get("components"))}

## Do's and Don'ts

### Do
{chr(10).join('- ' + x for x in dos)}

### Don't
{chr(10).join('- ' + x for x in donts)}
"""
    return md


def verify(md_dir: Path, rows: list[dict]) -> dict:
    pal = Counter()
    how = Counter()
    bodies = Counter()
    missing_sec = []
    yaml_mismatch = 0
    broken_ref = 0
    by_site = defaultdict(Counter)
    id_site = {r["id"]: r["sourceSite"] for r in rows}
    for p in sorted(md_dir.glob("sty-*.DESIGN.md")):
        t = p.read_text(encoding="utf-8")
        bodies[hashlib.md5(t.encode()).hexdigest()] += 1
        m = re.search(r'primary: "([^"]+)"', t)
        bg = re.search(r'background: "([^"]+)"', t)
        primary = m.group(1) if m else "?"
        pal[primary] += 1
        eid = p.name.split("__", 1)[0]
        by_site[id_site.get(eid, "?")][primary] += 1
        hm = re.search(r"^How to use: (.+)$", t, re.M)
        if hm:
            how[hm.group(1)] += 1
        for sec in SECTIONS:
            if f"## {sec}" not in t:
                missing_sec.append((p.name, sec))
        body_p = re.search(r"- \*\*primary\*\* \(`([^`]+)`\)", t)
        if body_p and m and body_p.group(1) != m.group(1):
            yaml_mismatch += 1
        for ref in re.findall(r"\{colors\.([A-Za-z0-9_]+)\}", t):
            if f"{ref}:" not in t.split("---", 2)[1]:
                broken_ref += 1
    unique_files = sum(1 for n in bodies.values() if n == 1)
    return {
        "files": sum(bodies.values()),
        "unique_files": unique_files,
        "unique_primaries": len(pal),
        "top_primaries": pal.most_common(8),
        "max_how_clone": how.most_common(1)[0][1] if how else 0,
        "unique_how": len(how),
        "missing_sections": len(missing_sec),
        "yaml_mismatch": yaml_mismatch,
        "broken_ref": broken_ref,
        "by_site": {k: {"n": sum(v.values()), "unique_primary": len(v), "top": v.most_common(1)[0]} for k, v in by_site.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Distill unique Google-spec DESIGN.md files for a style pack.")
    parser.add_argument("--root", type=Path, default=None, help="风格包根目录（含 catalog/ 与 design-md/）")
    args = parser.parse_args()
    configure(args.root.resolve() if args.root else find_pack_root(Path.cwd()))
    if not JSONL.exists():
        raise SystemExit(f"缺少 {JSONL}")
    MD_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(parents=True, exist_ok=True)

    rows = [json.loads(l) for l in JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    hashes = {}
    for rec in rows:
        shot = find_asset(rec["id"])
        if not shot:
            raise SystemExit(f"missing screenshot {rec['id']}")
        hashes[rec["id"]] = file_md5(shot)
    clone_n = Counter(hashes.values())

    old_files = {p.name for p in MD_DIR.glob("sty-*.DESIGN.md")}
    written = []
    origins = Counter()
    for i, rec in enumerate(rows, 1):
        eid = rec["id"]
        shot = find_asset(eid)
        assert shot
        cloned = clone_n[hashes[eid]] >= 8
        colors, origin, extra = resolve_palette(rec, shot, cloned)
        bucket = "voltagent" if extra.get("origin") == "voltagent" else ("cloned-title" if cloned else ("named" if "蒸馏" in origin else "screenshot"))
        origins[bucket] += 1
        slug = rec.get("slug") or eid
        fname = f"{eid}__{slug}.DESIGN.md"
        text = build_md(rec, colors, shot.name, origin, extra)
        (MD_DIR / fname).write_text(text, encoding="utf-8")
        written.append(fname)
        rec["screenshotPath"] = f"brand-style-assets/by-id/{shot.name}"
        rec["templatePath"] = f"design-md/{fname}"
        rec["paletteNotes"] = (
            f"{origin}；主色 {rgb_hex(colors['primary'])}，背景 {rgb_hex(colors['background'])}，"
            f"表面 {rgb_hex(colors['surface'])}"
        )
        if i % 200 == 0:
            print(f"... {i}/{len(rows)}")

    keep = set(written)
    removed = 0
    for name in old_files - keep:
        (MD_DIR / name).unlink()
        removed += 1

    JSONL.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    stats = verify(MD_DIR, rows)
    print("wrote", len(written), "removed stale", removed)
    print("unique files", stats["unique_files"], "/", stats["files"])
    print("unique primaries", stats["unique_primaries"], "top", stats["top_primaries"][:5])
    print("unique how-to", stats["unique_how"], "max clone", stats["max_how_clone"])
    print("yaml mismatch", stats["yaml_mismatch"], "broken refs", stats["broken_ref"], "missing sec", stats["missing_sections"])
    print("by site", stats["by_site"])
    print("origins", origins.most_common())

    summary = {
        "total": len(rows),
        "files": stats["files"],
        "method": "voltagent-yaml + unique-screenshot quantize + title-hue for cloned shots",
        "unique_files": stats["unique_files"],
        "unique_primaries": stats["unique_primaries"],
        "yaml_mismatch": stats["yaml_mismatch"],
        "broken_ref": stats["broken_ref"],
        "missing_sections": stats["missing_sections"],
        "by_site": stats["by_site"],
        "top_primaries": stats["top_primaries"],
    }
    (MD_DIR / "_GEN_SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    site_lines = "\n".join(
        f"- **{k}：** {v['n']} 条，独立主色 {v['unique_primary']}，最高频 {v['top'][0]} ×{v['top'][1]}"
        for k, v in stats["by_site"].items()
    )
    (MD_DIR / "_VERIFY_REPORT.md").write_text(
        f"""# DESIGN.md 蒸馏记录

- **条目：** {len(rows)}
- **规范：** Google Labs design.md alpha（YAML + {', '.join(SECTIONS)}）
- **色板：** VoltAgent YAML（品牌分析）/ 公开组件库与主题 / 独立截图量化 / 克隆截图按标题色相
- **重复：** 整文件互不相同 {stats['unique_files']}/{stats['files']}；主色 {stats['unique_primaries']} 种
- **YAML 与正文主色：** 不一致 {stats['yaml_mismatch']}；断裂 token {stats['broken_ref']}；缺节 {stats['missing_sections']}

{site_lines}

重新生成：`python3 scripts/distill_pack.py --root <pack>`
""",
        encoding="utf-8",
    )
    (ROOT / "logs" / "FIX-STATUS.md").write_text(
        "# Catalog Fix Status\n\n"
        "- DESIGN.md 已按 Google design.md alpha 全量重蒸馏：YAML + 八节正文。\n"
        "- 上游已是 DESIGN.md 时映射 YAML token，不整篇粘贴英文长文。\n"
        "- 克隆截图按条目标题与垂直领域蒸馏独立主色。\n"
        "- 独立截图量化取色；过灰则保留背景、主色走标题色相。\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
