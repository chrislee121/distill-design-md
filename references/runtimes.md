# 支持的 Agent Runtime

基于 [Agent Skills](https://agentskills.io) 协议。

## 推荐安装

```
帮我安装这个 skill：https://github.com/chrislee121/distill-design-md
```

```bash
npx skills add chrislee121/distill-design-md
```

指定 runtime 时加 `-a cursor` / `-a claude-code` / `-a codex` 等。

## 手动安装（用户级）

把本仓库放到对应 `skills/` 目录，目录名保持 `distill-design-md`：

| Runtime | 典型路径 |
|---------|----------|
| Cursor | `~/.cursor/skills/distill-design-md/` |
| Claude Code | `~/.claude/skills/distill-design-md/` |
| Codex | `~/.codex/skills/distill-design-md/` |
| OpenClaw | `~/.openclaw/workspace/skills/distill-design-md/` |
| Gemini CLI | `~/.gemini/skills/distill-design-md/` |
| OpenCode | `~/.config/opencode/skills/distill-design-md/` |

项目级也可放在 `.cursor/skills/`、`.agents/skills/`。
